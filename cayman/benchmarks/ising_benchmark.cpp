// Self-contained dense ferromagnetic Ising min-cut and ideal p=1 QAOA simulator.
// No provider SDKs, BLAS, dense unitaries, or hardware calls.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <complex>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <queue>
#include <random>
#include <string>
#include <vector>

using Clock = std::chrono::steady_clock;
using C = std::complex<double>;
constexpr double EPS = 1e-9;

struct Instance {
  int n;
  std::vector<double> h;  // h=A-r, deliberately mixed sign
  std::vector<double> j;  // full symmetric nonnegative matrix, J_ii=0
  double at(int a, int b) const { return j[static_cast<size_t>(a)*n+b]; }
};

Instance make_dense(int n, uint64_t seed) {
  std::mt19937_64 rng(seed + 0x9e3779b97f4a7c15ULL * static_cast<uint64_t>(n));
  std::uniform_real_distribution<double> u(0.0, 1.0);
  Instance x{n, std::vector<double>(n), std::vector<double>(static_cast<size_t>(n)*n, 0.0)};
  // Mixed local preferences stay comparable with total dense coupling.
  for (int i=0;i<n;i++) x.h[i] = 0.85*std::sin(0.73*(i+1)) + 0.45*(u(rng)-0.5);
  // Positive dense ties with O(1) total incident coupling, not a trivial uniform model.
  for (int i=0;i<n;i++) for (int k=i+1;k<n;k++) {
    double value = (0.25 + 0.75*u(rng)) / static_cast<double>(n);
    x.j[static_cast<size_t>(i)*n+k] = x.j[static_cast<size_t>(k)*n+i] = value;
  }
  return x;
}

double energy_from_index(const Instance& x, uint64_t state) {
  double e = 0;
  for (int i=0;i<x.n;i++) {
    double si = ((state >> i) & 1ULL) ? -1.0 : 1.0;  // bit 0 is digital, s=+1
    e -= x.h[i]*si;
    for (int k=i+1;k<x.n;k++) {
      double sk = ((state >> k) & 1ULL) ? -1.0 : 1.0;
      e -= x.at(i,k)*si*sk;
    }
  }
  return e;
}

struct Edge { int to, rev; double cap; };
struct Dinic {
  std::vector<std::vector<Edge>> g;
  std::vector<int> level, it;
  explicit Dinic(int n): g(n), level(n), it(n) {}
  void add(int u, int v, double c) {
    Edge a{v, static_cast<int>(g[v].size()), c}, b{u, static_cast<int>(g[u].size()), 0};
    g[u].push_back(a); g[v].push_back(b);
  }
  bool bfs(int s, int t) {
    std::fill(level.begin(), level.end(), -1); std::queue<int> q; level[s]=0; q.push(s);
    while (!q.empty()) { int v=q.front();q.pop(); for (const auto& e:g[v])
      if (e.cap > EPS && level[e.to]<0) level[e.to]=level[v]+1,q.push(e.to); }
    return level[t]>=0;
  }
  double dfs(int v, int t, double f) {
    if (v==t) return f;
    for (int& i=it[v]; i<(int)g[v].size(); ++i) {
      Edge& e=g[v][i];
      if (e.cap>EPS && level[v]<level[e.to]) {
        double d=dfs(e.to,t,std::min(f,e.cap));
        if (d>EPS) { e.cap-=d; g[e.to][e.rev].cap+=d; return d; }
      }
    }
    return 0;
  }
  double flow(int s, int t) {
    double ans=0, inf=std::numeric_limits<double>::infinity();
    while (bfs(s,t)) { std::fill(it.begin(),it.end(),0); double f; while ((f=dfs(s,t,inf))>EPS) ans+=f; }
    return ans;
  }
  std::vector<char> reachable(int s) const {
    std::vector<char> seen(g.size()); std::queue<int> q; seen[s]=1;q.push(s);
    while(!q.empty()) { int v=q.front();q.pop(); for(const auto& e:g[v]) if(e.cap>EPS&&!seen[e.to]) seen[e.to]=1,q.push(e.to); }
    return seen;
  }
};

struct Exact { double energy, cut; uint64_t state; };
Exact mincut(const Instance& x) {
  int s=x.n, t=x.n+1; Dinic d(x.n+2); double offset=0;
  for(int i=0;i<x.n;i++) {
    if(x.h[i]>0) d.add(s,i,2*x.h[i]); else if(x.h[i]<0) d.add(i,t,-2*x.h[i]);
    offset -= std::abs(x.h[i]);
  }
  for(int i=0;i<x.n;i++) for(int k=i+1;k<x.n;k++) if(x.at(i,k)>0) {
    d.add(i,k,2*x.at(i,k)); d.add(k,i,2*x.at(i,k)); offset-=x.at(i,k);
  }
  double cut=d.flow(s,t); auto side=d.reachable(s); uint64_t state=0;
  for(int i=0;i<x.n;i++) if(!side[i]) state|=(1ULL<<i); // sink side -> paper bit 1
  return {cut+offset,cut,state};
}

struct Eval { double expected, ground_prob, norm; };
Eval qaoa_eval(const std::vector<double>& e, int n, double gamma, double beta, double exact) {
  const uint64_t m=1ULL<<n;
  std::vector<C> psi(m, C(1/std::sqrt(static_cast<double>(m)),0));
  // cost: exp(-i gamma E(z)); energies are precomputed separately.
  for(uint64_t z=0;z<m;z++) psi[z] *= std::exp(C(0,-gamma*e[z]));
  // mixer: Rx(2 beta)=cos(beta)I-i sin(beta)X on each qubit, in place by pairs.
  double c=std::cos(beta), sn=std::sin(beta);
  for(int q=0;q<n;q++) for(uint64_t base=0;base<m;base+=(2ULL<<(q))) for(uint64_t off=0;off<(1ULL<<q);off++) {
    uint64_t a=base+off,b=a+(1ULL<<q); C va=psi[a],vb=psi[b];
    psi[a]=c*va-C(0,sn)*vb; psi[b]=c*vb-C(0,sn)*va;
  }
  double expected=0,norm=0,ground=0;
  for(uint64_t z=0;z<m;z++) { double p=std::norm(psi[z]); norm+=p; expected+=p*e[z]; if(std::abs(e[z]-exact)<1e-8) ground+=p; }
  return {expected,ground,norm};
}

std::vector<double> precompute_energies(const Instance& x) {
  // Gray-code traversal: O(n 2^n), explicitly timed as precomputation.
  // This replaces a misleading O(n^2 2^n) direct enumeration bottleneck.
  uint64_t m=1ULL<<x.n; std::vector<double> e(m); std::vector<double> spin(x.n, 1.0);
  double current=energy_from_index(x, 0); e[0]=current;
  for(uint64_t step=1;step<m;step++) {
    int q=__builtin_ctzll(step);  // bit flipped between Gray(step-1) and Gray(step)
    double local=x.h[q];
    for(int j=0;j<x.n;j++) if(j!=q) local+=x.at(q,j)*spin[j];
    current += 2*spin[q]*local;
    spin[q] = -spin[q];
    uint64_t gray=step^(step>>1);
    e[gray]=current;
  }
  return e;
}

double seconds(Clock::time_point start) { return std::chrono::duration<double>(Clock::now()-start).count(); }
void csv_header(std::ofstream& out) {
  out << "family,n,repeat,seed,graph_build_s,energy_precompute_s,mincut_s,qaoa_one_eval_s,qaoa_optimizer_s,"
         "qaoa_eval_count,exact_energy,qaoa_expected_energy,qaoa_ground_probability,qaoa_norm,status\n";
}
void row(std::ofstream& out,const std::string& family,int n,int rep,uint64_t seed,double build,double pre,double cut,
         double one,double opt,int evals,double exact,double expected,double gp,double norm,const std::string& status) {
  out<<family<<","<<n<<","<<rep<<","<<seed<<","<<build<<","<<pre<<","<<cut<<","<<one<<","<<opt<<","<<evals<<","
     <<exact<<","<<expected<<","<<gp<<","<<norm<<","<<status<<"\n";
}

bool tests() {
  // Tiny exact comparison and statevector invariants.
  for(int n=2;n<=5;n++) {
    Instance x=make_dense(n, 7); Exact cut=mincut(x); double brute=1e99;
    for(uint64_t z=0;z<(1ULL<<n);z++) brute=std::min(brute,energy_from_index(x,z));
    if(std::abs(cut.energy-brute)>1e-8) { std::cerr<<"mincut mismatch n="<<n<<"\n"; return false; }
    auto e=precompute_energies(x);
    for(uint64_t z=0;z<(1ULL<<n);z++) if(std::abs(e[z]-energy_from_index(x,z))>1e-10) {
      std::cerr<<"Gray-code energy mismatch n="<<n<<"\n"; return false;
    }
    auto phase=qaoa_eval(e,n,.37,0,cut.energy);
    auto zero_gamma=qaoa_eval(e,n,0,.43,cut.energy);
    double uniform=0; for(double v:e) uniform+=v/e.size();
    if(std::abs(phase.norm-1)>1e-10 || std::abs(phase.expected-uniform)>1e-10 ||
       std::abs(zero_gamma.norm-1)>1e-10 || std::abs(zero_gamma.expected-uniform)>1e-10) {
      std::cerr<<"QAOA invariant mismatch n="<<n<<"\n"; return false;
    }
  }
  return true;
}

int main(int argc,char** argv) {
  std::string mode=argc>1?argv[1]:"run", output=argc>2?argv[2]:"results/raw.csv";
  if(mode=="--test") { bool ok=tests(); std::cout<<(ok?"PASS\n":"FAIL\n"); return ok?0:1; }
  std::ofstream out(output); if(!out) { std::cerr<<"cannot open "<<output<<"\n"; return 2; } csv_header(out);
  const std::vector<int> common={4,6,8,10,12,14,16,18,20,22,24,26};
  const std::vector<int> classical={20,40,80,120,160,200,240,500,1000,2000};
  const std::vector<double> gammas={.2,.6,1.0}, betas={.2,.5,.8}; const int reps=3;
  // Untimed warmup avoids charging allocator/cache cold-start behavior to the first row.
  { Instance warm=make_dense(10, 1); Exact exact=mincut(warm); auto e=precompute_energies(warm);
    (void)qaoa_eval(e,10,.2,.2,exact.energy); }
  for(int n:common) for(int rep=0;rep<(n<=20 ? reps : (n==22 ? 2 : 1));rep++) {
    uint64_t seed=20261107ULL+1000*n+rep; auto start=Clock::now(); Instance x=make_dense(n,seed); double build=seconds(start);
    start=Clock::now(); Exact exact=mincut(x); double cut=seconds(start);
    start=Clock::now(); auto energies=precompute_energies(x); double pre=seconds(start);
    start=Clock::now(); Eval one=qaoa_eval(energies,n,gammas[0],betas[0],exact.energy); double one_s=seconds(start);
    start=Clock::now(); Eval best=one; for(double g:gammas) for(double b:betas) {
      Eval v=qaoa_eval(energies,n,g,b,exact.energy); if(v.expected<best.expected) best=v;
    } double opt=seconds(start);
    row(out,"common",n,rep,seed,build,pre,cut,one_s,opt,9,exact.energy,best.expected,best.ground_prob,best.norm,"completed");
    out.flush(); std::cerr<<"common n="<<n<<" rep="<<rep<<" done\n";
  }
  for(int n:classical) if(n>20) for(int rep=0;rep<reps;rep++) {
    uint64_t seed=20261107ULL+1000*n+rep; auto start=Clock::now(); Instance x=make_dense(n,seed); double build=seconds(start);
    start=Clock::now(); Exact exact=mincut(x); double cut=seconds(start);
    row(out,"classical_only",n,rep,seed,build,0,cut,0,0,0,exact.energy,0,0,0,"completed");
    out.flush(); std::cerr<<"classical n="<<n<<" rep="<<rep<<" done\n";
  }
}

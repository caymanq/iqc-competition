# iqc-competition

## Inspiration

We were inspired by quantum approaches to solving optimization problems with applications to Ising model simulations. Specifically, we were intrigued by the supposed computational benefits of quantum approximation optimization algorithms (QAOA), which propose an approximate speed up of \\(1\\) degree of polynomial time in contrast to standard classical methods. While we understand that the quantum hardware and software isn't adept enough yet to show these results empirically, we wanted to show that this algorithm could be executed on real quantum hardware, and that our results compare in accuracy to the classical solution.

## What it does

The QAOA that we used is a quantum circuit composed of quantum bits (qubits) and quantum gates. There are four main operations performed by these gates, which alter the form of the qubits. Each qubit, in our problem, represents whether or not a certain industry has gone digital. For example, if we list the industries numerically (i.e. \\(1, 2, 3, \dots, n\\)), then we can label some string of qubits \\(|011\dots0\rangle\\), where a zero corresponds to that industry remaining a "paper" industry, whereas a one would indicate that that industry would flip to a digital industry.

Our quantum circuit acts as follows:
1. We initialize a string of \\(n\\) qubits, and act on them with the _Hadamard_ gate, which puts all bits into a _superposition_ of zero and one, meaning that there is equal chance to measure each industry as either paper or digital.
2. We act on all qubits with a _cost_ gate, which adds information to each qubit that indicates which states each industry would prefer at that time.
3. We use a _mixing_ gate to transfer that information from the phase of the qubit into the probabilities of each bitwise outcome.
4. We can repeat the previous two steps a number of times, optimizing on certain parameters classically, making this a hybrid algorithm between classical and quantum computing.
5. We finally measure the state of each qubit, and the total state with the highest probability will be the optimal solution to the problem.

## How we built it

We used a variety of tools to help us develop our algorithms. To begin with, we decided that it would be best to understand the algorithm fundamentally, and manually work through a few test cases by hand. While tedious, this gave us an edge into understanding what the algorithm is doing behind the scenes, and allowed us to start to work with large-language AI models to draft some code to solving the base cases of the problem. We also worked though developing a classical solution using an Ising-model based minimization with the _minimum-cut_ algorithm to supply a benchmark for our quantum solutions.

Once we were able to get preliminary results, we decided to expand our dataset into regions, and work real data into our project. Finding ways to run this took time, but we eventually were able to come up with some solutions using the various tools we had.

One very helpful tool we had for running our simulations was qBraid. We were able to utilize many of the build-in workflows within the infrastructure to develop large quantum circuits as well as ...


## Challenges we ran into



## Accomplishments that we're proud of



## What we learned



## What's next?

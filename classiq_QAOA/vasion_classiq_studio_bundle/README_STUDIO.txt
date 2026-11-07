Vasion Classiq Studio - 20 qubit QAOA

1. In Classiq Studio (browser-based VS Code), create a folder and upload/extract all 4 files.
2. Open a Terminal in that folder.
3. Classiq is preinstalled in Studio. If scipy, numpy, pandas, or networkx are missing, run: pip install scipy numpy pandas networkx
4. Start with: python vasion_classiq_qaoa.py --year 2036 --shots 1024
5. Later try COBYLA: python vasion_classiq_qaoa.py --year 2036 --optimize --maxiter 60 --shots 1024
6. Run 15 years (no optimizer): python vasion_classiq_qaoa.py --all-years

Initial angles are [gamma1=0.7, beta1=-0.4, gamma2=0.7, beta2=-0.4], matching the improved unoptimized run.

The .py script synthesizes using Classiq Python SDK. The .qmod is an optional equivalent parameterized graphical Model-editor representation.

This script has not been run on authenticated Classiq cloud. If the SDK returns an error, save the traceback for troubleshooting.

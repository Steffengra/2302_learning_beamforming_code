
This code was used in the following publication [(preprint here)](https://arxiv.org/abs/2303.11427).

[1] Steffen Gracla, Alea Schröder, Maik Röper, Carsten Bockelmann, Dirk Wübben, Armin Dekorsy,
"Learning Model-Free Robust Precoding for Cooperative Multibeam Satellite Communications" ,
in *Proc. Signal and Data Processing for Next Generation Satellites (SDPNGS) Workshop of the
2023 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP)*,
Rhodes, Greece, 4. - 10. June 2023.

Email: {**gracla**, **schroeder**, roeper, bockelmann, wuebben, dekorsy}@ant.uni-bremen.de


The project structure is as follows:
```
/project/
|   .gitignore           | .gitignore
|   README.md            | this file
|   requirements.txt     | project dependencies
|   
+---models               | trained models
+---outputs              | generated results
+---references           | dev references
+---reports              | project reports
+---src                  | python files
|   +---analysis         | generating results
|   +---config           | configuration
|   +---data             | generating data to learn from
|   +---models           | related to creating learned models
|   +---plotting         | plotting
|   \---utils            | shared functions and code snippets
```
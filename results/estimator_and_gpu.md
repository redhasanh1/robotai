# Physics-informed estimator vs camera (simulation)

`tools/estimator_eval.py` - finger flexion error in degrees, mean of 3 seeds. Camera sees ~18% of samples (1 frame in 3, hidden half the time, 3% noise). "bend" is the case the estimator was developed against; the other three unmodelled-physics forms were HELD OUT.

```
unmodelled physics     camera only  physics only       +camera        +sysid     +residual
bend (dev)                    16.0           6.3           6.1           5.4           1.7
quad (held out)               15.9          12.1          11.7          11.2           2.7
stick (held out)              14.7           4.4           4.3           0.8           0.8
asym (held out)               15.6           3.5           3.4           2.3           1.9

```

# NVIDIA MuJoCo Warp on GTX 1660 Ti

| candidates | time (warm) | per candidate | agrees with CPU |
|---|---|---|---|
| 16 | 0.72 s | 45 ms | 15/16 |
| 256 | 1.01 s | 3.9 ms | |
| 1024 | 1.92 s | 1.9 ms | |

CPU reference: 65 ms/candidate serial, 16 candidates in 0.18 s on an 8-process pool.

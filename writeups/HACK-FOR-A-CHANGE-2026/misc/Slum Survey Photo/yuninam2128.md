---
ctf_name: "HACK FOR A CHANGE 2026"
challenge_name: "Slum Survey Photo"
category: "misc"
difficulty: "easy"
author: "yuninam2128"
date: "2026-05-19"
points: 100
tags: [forensics, png, trailing-data, file-format, strings]
---

# MTaquitous

## 문제 설명

취약점을 찾아 공격하여 flag 파일을 읽어주세요.

- 문제 URL / 파일 등 참고 정보:

## 풀이

### 분석

문제에서 제공된 `navigate.py`를 보면 내부 상태값 `sval`은 다음 식으로 갱신된다.

```python
self.sval = (a * self.sval + b) % self.P
```

형태만 보면 전형적인 LCG이다. 다만 이 문제에서는 하나의 고정된 `(a, b)`를 사용하는 것이 아니라, 여러 상태가 존재하고 각 상태마다 서로 다른 `(a, b)`를 가진다.

출력 과정은 다음과 같다.

1. 현재 상태의 `(a, b)`로 `sval`을 한 번 갱신한다.
2. 갱신된 값을 로그북에 기록한다.
3. 마르코프 전이 행렬에 따라 다음 상태를 선택한다.
4. 마지막에는 `lcg.next() & 0xff` 값을 키스트림으로 사용해 플래그와 XOR 한다.

따라서 이 문제의 핵심은 두 가지다.

1. 로그북에 있는 850개의 출력값만으로 모듈러스 `P`를 복구한다.
2. 반복적으로 등장하는 `(a, b)` 쌍을 찾아 상태를 복원한 뒤, ciphertext를 복호화한다.

### 취약점

상태가 바뀌는 구간에서는 서로 다른 LCG가 섞이기 때문에 단순한 LCG 분석이 바로 통하지 않는다. 하지만 같은 상태가 연속으로 유지되는 구간에서는 완전히 평범한 LCG처럼 동작한다.

관측값을 `x_i`라고 두면, 같은 상태에서 다음 관계가 성립한다.

```text
x_{i+1} = a x_i + b mod P
x_{i+2} = a x_{i+1} + b mod P
```

여기서 차분을 `d_i = x_{i+1} - x_i`라고 하면 다음 관계가 나온다.

```text
d_{i+1} = a d_i mod P
```

따라서 같은 상태가 충분히 연속으로 유지된 구간에서는 다음 식이 성립한다.

```text
d_{i+2} * d_i - d_{i+1}^2 ≡ 0 mod P
```

즉, 로그북에서 이 값을 많이 만든 뒤 GCD를 구하면 `P`의 배수를 얻을 수 있다. 충분히 많은 구간을 사용하면 실제 모듈러스 `P`가 복원된다.

`P`를 복구한 뒤에는 연속된 세 관측값 `(x_i, x_{i+1}, x_{i+2})`로부터 `(a, b)` 후보를 계산할 수 있다.

```text
a = (x_{i+2} - x_{i+1}) * (x_{i+1} - x_i)^(-1) mod P
b = x_{i+1} - a x_i mod P
```

진짜 상태에서 나온 `(a, b)`는 여러 번 반복해서 등장한다. 반면 상태가 바뀌는 경계에서 계산된 가짜 `(a, b)`는 대부분 한 번만 등장한다. 따라서 빈도수를 세면 실제 상태의 파라미터를 복원할 수 있다.

### 익스플로잇

먼저 로그북에서 관측값을 파싱하고, 차분 기반 식을 이용해 `P`를 복구한다.

```python
import re
import ast
from math import gcd
from functools import reduce

text = open("logbook.txt").read()
obs = ast.literal_eval(re.search(r'Log: (\[.*\])\nCiphertext', text, re.S).group(1))

diffs = [obs[i + 1] - obs[i] for i in range(len(obs) - 1)]

T = [
    diffs[i + 2] * diffs[i] - diffs[i + 1] * diffs[i + 1]
    for i in range(len(diffs) - 2)
]

vals = []

for i in range(len(T) - 2):
    a, b, c = T[i:i + 3]

    if a and b and c:
        g = gcd(gcd(abs(a), abs(b)), abs(c))

        if g > 1:
            vals.append(g)

P = reduce(gcd, [v for v in vals if v.bit_length() > 100])

print(P)
```

복구된 `P`는 다음과 같다.

```text
114998001088122878165469494209865851580646945385760011250661037287215114047884823814201471683151719773292295650809857617855325511069020132311210674811529707856845753203740687736866355160800098819362158152761107736460621045328980768188047601931528470157
```

이제 모든 연속된 세 값에 대해 `(a, b)` 후보를 계산하고 빈도수를 센다.

```python
from collections import Counter

ctr = Counter()

for i in range(len(obs) - 2):
    x0, x1, x2 = [x % P for x in obs[i:i + 3]]

    d0 = (x1 - x0) % P
    d1 = (x2 - x1) % P

    if d0 == 0:
        continue

    a = d1 * pow(d0, -1, P) % P
    b = (x1 - a * x0) % P

    if (a * x1 + b) % P == x2:
        ctr[(a, b)] += 1

for (a, b), cnt in ctr.most_common(5):
    print(cnt, a, b)
```

상위 5개의 `(a, b)` 쌍이 압도적으로 많이 등장한다. 이 5개가 실제 마르코프 체인의 상태에 해당한다.

이제 복구한 5개의 상태를 이용하면 로그값 사이의 전이를 라벨링할 수 있고, 마지막 관측값 이후의 상태열만 추정하면 된다.

마지막 복호화에서는 `obs[849]`를 시작 상태값으로 두고, 가능한 다음 상태를 따라가며 `next() & 0xff`를 키스트림 바이트로 만든다. 이후 ciphertext와 XOR 하여 평문 후보를 만든다.

플래그 포맷이 `RS{...}`인 점을 이용해 빔서치로 후보를 줄이면 정답이 하나로 수렴한다.

```python
import math

ct = bytes.fromhex(re.search(r'Ciphertext: ([0-9a-f]+)', text).group(1))

heads = [
    # 복구한 5개 (a, b)
]

trans = [
    [140, 13, 18, 12, 16],
    [8, 118, 13, 12, 13],
    [21, 6, 114, 12, 12],
    [10, 20, 12, 112, 19],
    [20, 6, 8, 25, 88],
]

probs = [[c / sum(row) for c in row] for row in trans]

charset = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_{}")
prefix = "RS{"

beam = [(0.0, 4, obs[-1] % P, "")]

for depth in range(len(ct)):
    new_beam = []

    for score, st, sval, plain in beam:
        for ns, (a, b) in enumerate(heads):
            nxt = (a * sval + b) % P
            ch = chr((nxt & 0xff) ^ ct[depth])

            if ch not in charset:
                continue

            cand = plain + ch

            if depth < len(prefix) and cand != prefix[:depth + 1]:
                continue

            if cand[:3] != "RS{":
                continue

            if "}" in cand[:-1]:
                continue

            new_beam.append((score - math.log(probs[st][ns]), ns, nxt, cand))

    beam = sorted(new_beam, key=lambda x: x[0])[:5000]

for item in beam:
    if item[3].endswith("}"):
        print(item[3])
        break
```

최종적으로 다음 플래그를 얻을 수 있었다.

## 플래그

```text
RS{w04h_h1dd3n_M4rk0v_br34k5_LCGs}
```

## 배운 점

상태 전이가 섞여 있어도, 같은 상태가 충분히 오래 유지되는 구간이 있으면 LCG의 구조가 그대로 드러난다.

특히 `d_{i+2} * d_i - d_{i+1}^2` 형태의 값을 이용해 모듈러를 복구하는 고전적인 LCG 분석 기법이, 마르코프 체인과 결합된 변형 LCG에도 그대로 통한다는 점이 핵심이었다.
---
ctf_name: "HyperSonicCTF-2026"
challenge_name: "NORfuscated"
category: "rev"
difficulty: "medium"
author: "ttzero25"
date: "2026-06-07"
points: 739
tags: [Rust, Circuit-SAT, NOR Gate, PySAT]
---

# 문제명
NORfuscated

## 문제 개요

문제를 실행하면 플래그를 입력받고, 올바른 플래그일 경우 `Correct!`를 출력한다.

처음에는 일반적인 문자열 비교 문제로 보였지만, 분석 결과 바이너리 내부에 거대한 논리 회로(Logic Circuit)가 포함되어 있었고, 입력값이 해당 회로를 통과하는지 여부를 검증하는 구조였다.

## 정적 분석

### 바이너리 확인

`file` 명령으로 확인하면 다음과 같다.

```text
ELF 64-bit LSB pie executable, x86-64, stripped, for GNU/Linux
```

또한 바이너리 내부에서 다음과 같은 Rust panic 문자열을 확인할 수 있었다.

```text
called Option::unwrap() on a None value
entered unreachable code
```

따라서 Rust로 작성된 바이너리임을 알 수 있다.

섹션 크기를 확인해보면 특이한 점이 있었다.

```text
.text    0x40200
.rodata  0x3f5ad0
```

일반적인 CTF 문제와 비교했을 때 `.rodata` 섹션이 지나치게 크다. 약 4MB 이상의 데이터가 저장되어 있으며, 단순 문자열이 아니라 검증용 데이터 구조가 포함되어 있을 것으로 추측하였다.

### main 함수 분석

`Enter flag:` 와 `Correct!` 문자열을 참조하는 함수를 따라가면 실제 검증 로직을 확인할 수 있다.

전체 흐름은 다음과 같다.

1. 사용자 입력을 받는다.
2. 입력 길이가 정확히 68바이트인지 확인한다.
3. 입력 바이트를 비트 단위로 분해한다.
4. `.rodata`에 저장된 회로 객체를 역직렬화한다.
5. 입력 비트를 회로의 입력 wire에 설정한다.
6. 모든 게이트를 순서대로 평가한다.
7. 최종 출력 wire가 1이면 `Correct!`를 출력한다.

길이 검사 부분은 다음과 같다.

```asm
cmp rax, 0x44
```

따라서 플래그 길이는 정확히 68바이트이다.

## 회로 분석

### 게이트 평가 함수

게이트 평가 함수는 다음과 같은 형태였다.

```asm
mov eax, [rdx+rbx]
mov ecx, [rdx+rbx+4]
mov r8d,[rdx+rbx+8]

mov r8d,[r10+8*r8]
or  r8d,[r10+8*rcx]

not r8d
and r8d, 1

mov [r10+8*rax], r8
```

이를 의사코드로 표현하면 다음과 같다.

```python
wires[out] = not (wires[in1] or wires[in2])
```

즉 모든 게이트는 NOR 게이트로 구성되어 있다.

문제 이름인 **NORfuscated** 역시 여기서 유래한 것으로 보인다.

## 회로 구조 추출

역직렬화 루틴을 분석하여 `.rodata` 내부의 데이터를 파싱하였다.

구조는 다음과 같다.

```text
[u32 gate_count]

gate_count × (
    u32 out,
    u32 in1,
    u32 in2
)

[u32 output_count]
[u32 output_wire]

[u32 input_count]

input_count × (
    u32 len,
    len × u32
)
```

파싱 결과는 다음과 같았다.

```text
Gate Count  : 344048
Output Count: 1
Output Wire : 344592
Input Count : 68
```

Wire 구성은 다음과 같다.

```text
wire 0            = 상수 0
wire 1~544        = 입력 비트
wire 545~344592   = 게이트 출력
```

즉 총 544개의 입력 비트와 344,048개의 NOR 게이트로 구성된 거대한 논리 회로였다.

초기 게이트 일부를 확인하면 다음과 같다.

```text
(545, 1, 1)
(546, 545, 545)
```

이는 다음 연산과 동일하다.

```text
wire545 = NOT(w1)
wire546 = NOT(wire545) = w1
```

즉 NOR 게이트만을 사용하여 NOT, AND, OR, XOR 등을 구현하고 있음을 확인할 수 있었다.

## SAT 문제로 변환

최종 목표는 출력 wire인 `344592`가 1이 되도록 하는 입력 비트를 찾는 것이다.

이는 전형적인 Circuit-SAT 문제로 볼 수 있다.

NOR 게이트는 다음과 같다.

```text
out = NOT(a OR b)
```

이를 Tseitin Encoding으로 CNF로 변환하면 다음과 같다.

```text
(¬out ∨ ¬a)
∧
(¬out ∨ ¬b)
∧
(out ∨ a ∨ b)
```

추가적으로 다음 조건을 부여한다.

```text
wire0 = false
output_wire = true
```

이후 PySAT의 Glucose3 Solver를 사용하여 전체 회로를 SAT 문제로 해결하였다.

```python
import pickle
from pysat.solvers import Glucose3

c = pickle.load(open("circuit.pkl", "rb"))

gates = c["gates"]
outs = c["outs"]
inputs = c["inputs"]

def V(w):
    return w + 1

clauses = [[-V(0)]]

for o, a, b in gates:
    clauses.append([-V(o), -V(a)])
    clauses.append([-V(o), -V(b)])
    clauses.append([V(o), V(a), V(b)])

clauses.append([V(outs[0])])

solver = Glucose3(bootstrap_with=clauses)

assert solver.solve()

model = solver.get_model()

values = {
    abs(x) - 1: int(x > 0)
    for x in model
}

flag = bytes(
    sum(values.get(inputs[i][j], 0) << j for j in range(8))
    for i in range(68)
)

print(flag.decode())
```

약 34만 개의 변수와 100만 개 이상의 절이 생성되지만, Glucose3는 매우 빠르게 해를 찾을 수 있었다.

## 검증

복구한 플래그를 다시 회로에 입력하여 직접 시뮬레이션하였다.

```python
w = [0] * N

for i in range(68):
    for j in range(8):
        w[inputs[i][j]] = (flag[i] >> j) & 1

for o, a, b in gates:
    w[o] = 1 - (w[a] | w[b])

assert w[outs[0]] == 1
```

최종 출력 wire가 1이 되는 것을 확인하였고, 프로그램에서도 정상적으로 `Correct!`가 출력되었다.

## Flag

```text
HS{REDACTED}
```

## 마무리

이 문제는 일반적인 문자열 비교 로직 대신 거대한 NOR 게이트 회로를 이용하여 플래그를 검증하는 문제였다.

회로를 직접 분석하여 원래 비교식을 복원하는 방법도 가능하겠지만, SAT Solver를 이용하면 훨씬 효율적으로 해결할 수 있다. 대규모 논리 회로를 CNF로 변환한 뒤 SAT Solver에 넘기는 전형적인 Circuit-SAT 풀이를 적용할 수 있었던 문제였다.

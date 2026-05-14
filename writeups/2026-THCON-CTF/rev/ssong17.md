---
ctf_name: "THCON"
challenge_name: "M4terM4xima's HINT (part 1/2)"
category: "rev"           # web / pwn / rev / crypto / misc
difficulty: "easy"      # easy / medium / hard / insane
author: "ssong17"
date: "2026-05-08"
points: 50
tags: [태그1, 태그2]
---

# 문제명

## 문제 설명

S.N.A.F.U. agents Have recovered this mysterious yet seemingly inoffensive binary... or is it really ?

- 문제 URL / 파일 등 접속 정보: archive.tar 파일

## 풀이

### 분석

바이너리는 RISC-V 32비트 정적 링크 ELF 실행 파일이다. 파일 내부에 심볼이 남아있어 main, HINT, maybe_HINT 등의 주요 함수 식별이 가능하다.

.rodata 섹션에는 "Are you sure this is a HINT?"와 같은 문자열과 함께 암호화된 플래그로 추정되는 20바이트의 데이터(011c0b3817191c495a1f171d430c4f174903014e)가 하드코딩되어 있다. maybe_HINT 함수의 디스어셈블리 코드를 확인하면, 입력받은 문자열을 순회하며 특정 XOR 연산을 수행한 뒤 .rodata의 데이터와 비교하는 로직이 존재한다.

### 취약점

maybe_HINT 함수에 구현된 암호화 로직은 단순한 XOR 체인이다.
어셈블리 코드를 보면 초기 키 값으로 0x55(85)를 사용하며, 다음과 같은 연산을 수행한다.

- transformed[0] = input[0] ^ 0x55
- transformed[i] = input[i] ^ input[i-1]

검증에 사용되는 20바이트의 결과값이 메모리에 평문으로 노출되어 있고, 연산 과정에서 데이터 손실이 없으므로 역연산을 통해 원본 입력값을 쉽게 복구할 수 있다.

### 익스플로잇
하드코딩된 암호화 배열을 가져와, 첫 번째 바이트는 0x55와 XOR하고 이후 바이트들은 바로 직전에 복구된 평문 바이트와 XOR하여 원본 플래그를 도출한다.

```python
enc = bytes.fromhex('011c0b3817191c495a1f171d430c4f174903014e')

res = bytearray(len(enc))
res[0] = enc[0] ^ 0x55
for i in range(1, len(enc)):
    res[i] = enc[i] ^ res[i-1]

print(res.decode())
```

## 플래그

```
THC{lui zero, ox123}
```

## 배운 점


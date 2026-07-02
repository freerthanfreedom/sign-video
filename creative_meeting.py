#!/usr/bin/env python3
"""5인 에이전트 창의 회의 시뮬레이터.

서로 다른 페르소나를 가진 5개의 에이전트가 하나의 주제를 놓고 회의를 진행한다.
이연연상(bisociation) 라운드에서는 주제와 무관한 자극어를 강제로 결합시켜
평범한 브레인스토밍에서 나오기 어려운 아이디어를 끌어낸다.

사용법:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 creative_meeting.py "서명 동영상 앱의 다음 버전 아이디어"

회의 순서:
    1라운드  발산      — 각 에이전트가 자기 관점에서 아이디어 제안
    2라운드  이연연상  — 랜덤 자극어 2개를 주제와 강제 결합
    3라운드  비평·결합 — 다른 에이전트의 아이디어를 비판하고 두 개를 합쳐 발전
    4라운드  수렴      — 진행자가 최종 컨셉 3개로 종합

결과는 콘솔에 실시간 출력되고 meeting_result.md 로 저장된다.
"""

import argparse
import random
import sys
from datetime import datetime

import anthropic

MODEL = "claude-opus-4-8"

# 페르소나 5인. 각자 관점이 겹치지 않도록 역할을 분리했다.
# 이전에 논의한 다른 5개 캐릭터가 있다면 이 딕셔너리만 교체하면 된다.
AGENTS = {
    "몽상가": (
        "당신은 '몽상가'다. 예술가이자 SF 작가의 감성을 가진 사람. "
        "실현 가능성은 전혀 신경 쓰지 않고, 감정·아름다움·서사의 관점에서만 말한다. "
        "뻔한 아이디어가 나오면 노골적으로 지루해한다. 비유와 이미지로 말하는 버릇이 있다."
    ),
    "공학자": (
        "당신은 '공학자'다. 실제로 만들 수 있는가, 며칠이면 되는가만 본다. "
        "다른 사람의 뜬구름 아이디어에서 '오늘 밤에 프로토타입 가능한 조각'을 끄집어내는 데 능하다. "
        "말이 짧고 구체적이다. 기술 제약을 창의적 재료로 쓴다."
    ),
    "관찰자": (
        "당신은 '관찰자'다. 사용자 심리 전문가. 사람들이 왜 그 행동을 하는지, "
        "무엇이 부끄럽고 무엇이 자랑하고 싶은지를 파고든다. "
        "아이디어가 나올 때마다 '실제 사용자는 그 순간 무슨 감정일까'를 되묻는다."
    ),
    "반골": (
        "당신은 '반골'이다. 모든 전제를 뒤집는 사람. '왜 꼭 그래야 하지?'가 입버릇. "
        "다수가 동의하는 방향이 보이면 일부러 정반대를 주장해 본다. "
        "파괴적이지만 악의는 없고, 뒤집기에서 새 길이 열리는 걸 즐긴다."
    ),
    "연결자": (
        "당신은 '연결자'다. 이연연상(bisociation)의 화신. 전혀 무관해 보이는 두 영역을 "
        "붙여서 제3의 것을 만드는 게 특기다. 요리와 암호학, 장례식과 게임처럼 "
        "멀리 떨어진 도메인에서 구조적 유사성을 찾아낸다. '그거 ○○랑 똑같은 구조인데?'가 말버릇."
    ),
}

FACILITATOR_SYSTEM = (
    "당신은 창의 회의의 진행자다. 회의록 전체를 읽고 아이디어들을 종합한다. "
    "안전한 아이디어보다 낯설지만 울림 있는 아이디어를 높게 평가한다. "
    "최종 결과물은 실행할 사람이 바로 움직일 수 있을 만큼 구체적이어야 한다."
)

# 이연연상 라운드용 자극어 풀 — 주제와 최대한 먼 도메인에서 고른다.
STIMULUS_POOL = [
    "심해 아귀", "발효", "장례식", "복화술", "이끼", "환전소", "철새의 V자 편대",
    "유리 부는 장인", "소매치기", "동굴 벽화", "재즈 즉흥연주", "탈피하는 뱀",
    "우편함", "등대지기", "곰팡이 네트워크", "주름", "시계태엽", "메아리",
]


def speak(client: anthropic.Anthropic, system: str, transcript: str,
          instruction: str, max_tokens: int = 2000) -> str:
    """에이전트 한 명의 발언을 스트리밍으로 받아 출력하고 반환한다."""
    prompt = (
        f"지금까지의 회의록:\n---\n{transcript}\n---\n\n"
        f"[진행자 지시]\n{instruction}\n\n"
        "당신의 페르소나를 유지하며 발언하라. 다른 참가자의 발언을 이름으로 인용해도 좋다. "
        "발언은 한국어로, 핵심만 담아 간결하게."
    )
    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        message = stream.get_final_message()
    print("\n")
    return next(b.text for b in message.content if b.type == "text")


def main() -> None:
    parser = argparse.ArgumentParser(description="5인 에이전트 창의 회의")
    parser.add_argument("topic", nargs="?",
                        default="서명 동영상 앱(sign-video)의 다음 버전을 특별하게 만들 아이디어")
    parser.add_argument("--seed", type=int, help="자극어 선택 시드(재현용)")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    client = anthropic.Anthropic()
    transcript = f"[회의 주제] {args.topic}\n"

    def record(name: str, round_name: str, text: str) -> None:
        nonlocal transcript
        transcript += f"\n### {name} ({round_name})\n{text}\n"

    # ---- 1라운드: 발산 ----
    print(f"\n{'='*60}\n회의 주제: {args.topic}\n{'='*60}\n")
    print("── 1라운드: 발산 ──────────────────────────\n")
    for name, persona in AGENTS.items():
        print(f"◆ {name}:")
        text = speak(client, persona, transcript,
                     "이 주제에 대해 당신의 관점에서 아이디어 3개를 제안하라. "
                     "남들이 이미 말한 것과 겹치지 않게.")
        record(name, "발산", text)

    # ---- 2라운드: 이연연상 ----
    stimuli = random.sample(STIMULUS_POOL, 2)
    print(f"── 2라운드: 이연연상 — 자극어: {stimuli[0]}, {stimuli[1]} ──\n")
    for name, persona in AGENTS.items():
        print(f"◆ {name}:")
        text = speak(client, persona, transcript,
                     f"자극어 '{stimuli[0]}'와(과) '{stimuli[1]}' 중 하나 이상을 골라, "
                     f"그것과 회의 주제를 강제로 결합한 아이디어 1~2개를 만들어라. "
                     "표면적 유사성이 아니라 구조적 유사성으로 연결할 것. 억지스러워도 좋다.")
        record(name, "이연연상", text)

    # ---- 3라운드: 비평과 결합 ----
    print("── 3라운드: 비평과 결합 ────────────────────\n")
    for name, persona in AGENTS.items():
        print(f"◆ {name}:")
        text = speak(client, persona, transcript,
                     "회의록에서 (1) 가장 약하다고 생각하는 남의 아이디어 하나를 골라 이유와 함께 비판하고, "
                     "(2) 서로 다른 참가자의 아이디어 두 개를 골라 결합해 더 나은 아이디어 하나로 발전시켜라.")
        record(name, "비평과 결합", text)

    # ---- 4라운드: 수렴 ----
    print("── 4라운드: 진행자 종합 ────────────────────\n")
    final = speak(client, FACILITATOR_SYSTEM, transcript,
                  "회의 전체를 종합해 최종 컨셉 3개를 뽑아라. 각 컨셉마다 "
                  "① 이름 ② 한 문단 설명 ③ 어떤 발언들의 충돌/결합에서 나왔는지 "
                  "④ 프로토타입 첫걸음 을 적어라. 마지막에 가장 추천하는 1개와 이유를 밝혀라.",
                  max_tokens=4000)
    record("진행자", "수렴", final)

    # ---- 저장 ----
    out_path = "meeting_result.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# 창의 회의록 — {datetime.now():%Y-%m-%d %H:%M}\n")
        f.write(f"\n자극어: {', '.join(stimuli)}\n")
        f.write(transcript)
    print(f"\n회의록 저장 완료: {out_path}")


if __name__ == "__main__":
    try:
        main()
    except anthropic.AuthenticationError:
        sys.exit("ANTHROPIC_API_KEY 환경변수를 설정한 뒤 다시 실행하세요.")
    except KeyboardInterrupt:
        sys.exit("\n회의 중단됨.")

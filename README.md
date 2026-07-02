# sign-video

서명 동영상 앱 (`index.html`).

## creative_meeting.py — 5인 에이전트 창의 회의

서로 다른 페르소나를 가진 5개의 AI 에이전트(몽상가·공학자·관찰자·반골·연결자)가
하나의 주제를 놓고 회의를 진행해 창의적인 컨셉을 뽑아내는 스크립트.
이연연상(bisociation) 라운드에서 주제와 무관한 자극어를 강제 결합시킨다.

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python3 creative_meeting.py "서명 동영상 앱의 다음 버전 아이디어"
```

회의는 발산 → 이연연상 → 비평·결합 → 수렴 4라운드로 진행되며,
결과는 콘솔에 실시간 출력되고 `meeting_result.md`로 저장된다.
페르소나를 바꾸려면 스크립트 상단의 `AGENTS` 딕셔너리를 수정하면 된다.

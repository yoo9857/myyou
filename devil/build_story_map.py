"""Author the story map for The Devil All The Time from the reference's structure.

The reference review of this same film was measured, not imitated. What carries over is
its shape:

  - It tells the film's interleaved threads one character group at a time instead of
    cross-cutting, which is easier to follow than the film's own order.
  - It spends a third of its runtime on the closing confrontations and disposes of setup
    beats in single six-second blocks.
  - Arvin and Lenora hold 62 percent of its narration; Willard, who opens the review, holds
    20 and exists to explain Arvin.
  - It leaves the film's own dialogue running in about ten long blocks, saved for the
    confrontations rather than sprinkled evenly.
  - It closes on one unbroken block: theme, then how to read the protagonist, then the cast.

What does not carry over is its ending. That review states who dies and who walks away;
this one stops on the raised guns, at the last line before the shooting.

Written in English because the review is narrated in English. Planning the beats in Korean
and translating afterwards is how narration ends up reading like a translation.

Source timings come from the film's embedded English subtitle track, read scene by scene.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "story_map.v1.json"

# The cut lands on the last line before the shooting. Bodecker calls Arvin out at 7408,
# both men draw, and the film's subtitles stop at 7563.92 - "You let loose that gun and
# I'll show it to you!" - with nothing for the next 50 seconds because that gap is the
# shootout. The first line after it, 7615, is Bodecker already dying, and 7644 states the
# outcome outright. Ending at 7570 keeps the guns raised and the plea unanswered: the
# viewer knows a shot is coming and not who fires.
SPOILER_CUTOFF = 7570.0  # 126:10

M = 60.0


def ev(eid, start, end, summary, visible, stake, opened, *, causes=(), chars=(),
       role="none", narration_at=None, evidence_at=None, intervals=None,
       must_show=True, answered=None, entry=False, transition="cut", reveal=None):
    interval_list = [list(i) for i in (intervals or [[start, end]])]
    return {
        "id": eid,
        "source_start": round(start, 3),
        "source_end": round(end, 3),
        "summary": summary,
        "cause_ids": list(causes),
        "entry_point": entry,
        "characters": list(chars),
        "visible_action": visible,
        "emotional_stake": stake,
        "question_opened": opened,
        "question_answered": answered,
        "reveal_time": round(reveal if reveal is not None else start, 3),
        "must_show": must_show,
        "selected_intervals": interval_list,
        "narration_role": role,
        "narration_start_time": None if narration_at is None else round(narration_at, 3),
        "narration_evidence_time": None if evidence_at is None else round(evidence_at, 3),
        "transition_in": transition,
        "needs_visual_review": True,
    }


sections = [
    {
        "id": "cold_open_prayer_log",
        "status": "draft",
        "audience_question": "Why is this man kneeling at a cross in the woods?",
        "exit_answer": None,
        "next_question": "When did the praying start?",
        "events": [
            ev("prayer_log_present", 22.4 * M, 23.6 * M,
               "Willard kneels at a cross he built in the woods, his son beside him",
               "A father and son on their knees at a log cross, the wood dark with blood",
               "The ritual arrives with no explanation, which is exactly why it holds",
               "What is this prayer trying to hold back?",
               chars=["Willard", "Arvin"], role="orient",
               narration_at=22.5 * M, evidence_at=22.4 * M,
               intervals=[[22.4 * M, 23.2 * M]], entry=True, transition="opening"),
        ],
    },
    {
        "id": "willard_war_and_charlotte",
        "status": "draft",
        "audience_question": "Where did Willard get this faith?",
        "exit_answer": None,
        "next_question": "What holds the family he builds together?",
        "events": [
            ev("crucified_soldier", 4.0 * M, 5.4 * M,
               "In the Pacific, Willard finds a US soldier nailed up and still alive",
               "A man lashed to a cross, maggots, Willard raising his sidearm",
               "Everything he later does with God starts here",
               "What does that leave in him?",
               causes=["prayer_log_present"], chars=["Willard"], role="causal_bridge",
               narration_at=4.6 * M, evidence_at=4.0 * M,
               intervals=[[4.0 * M, 5.0 * M]]),
            ev("meets_charlotte", 8.6 * M, 10.0 * M,
               "On the way home he sees Charlotte in a diner and says nothing",
               "A diner counter, a waitress, a man walking out without a word",
               "His silence is what lets his mother start arranging his life",
               "Will he come back for her?",
               causes=["crucified_soldier"], chars=["Willard", "Charlotte"], role="none",
               intervals=[[8.6 * M, 9.6 * M]]),
            ev("emma_matchmaking", 10.0 * M, 11.0 * M,
               "His mother Emma lines him up with Helen from her church",
               "A conversation outside the church, mother and son",
               "Two marriages get decided in one conversation",
               "Which woman does he choose?",
               causes=["meets_charlotte"], chars=["Willard", "Emma", "Helen"],
               role="rule_clarify", narration_at=10.2 * M, evidence_at=10.0 * M,
               intervals=[[10.0 * M, 10.8 * M]]),
        ],
    },
    {
        "id": "roy_and_helen_parallel",
        "status": "draft",
        "audience_question": "What became of the other couple from that same church?",
        "exit_answer": None,
        "next_question": "How far will that kind of faith go?",
        "events": [
            ev("roy_spider_sermon", 11.8 * M, 13.4 * M,
               "Roy the preacher pours a jar of spiders over his own head to prove his faith",
               "A pulpit, a jar of spiders, a congregation coming apart",
               "Summarising this would kill it, so the scene has to play",
               "What kind of person falls for this man?",
               causes=["emma_matchmaking"], chars=["Roy", "Helen", "Theodore"], role="none",
               intervals=[[11.9 * M, 12.9 * M]]),
            ev("helen_chooses_roy", 13.4 * M, 14.4 * M,
               "Helen takes it as a sign and chooses him",
               "Helen's face after the service, moving toward him",
               "This is the choice the rest of her life answers for",
               "How does this marriage end?",
               causes=["roy_spider_sermon"], chars=["Roy", "Helen"], role="stakes",
               narration_at=13.6 * M, evidence_at=13.4 * M,
               intervals=[[13.4 * M, 14.2 * M]]),
        ],
    },
    {
        "id": "arvin_boyhood",
        "status": "draft",
        "audience_question": "What does the father teach the son?",
        "exit_answer": None,
        "next_question": "When does that lesson get used?",
        "events": [
            ev("arvin_bullied", 20.4 * M, 21.6 * M,
               "Arvin gets worked over by older boys on the school bus",
               "A bus seat, a swollen eye, a boy keeping his head down",
               "He is carrying it alone, and his father notices",
               "How does his father step in?",
               causes=["meets_charlotte"], chars=["Arvin"], role="none",
               intervals=[[20.6 * M, 21.4 * M]]),
            ev("willard_teaches_revenge", 24.0 * M, 25.6 * M,
               "Willard teaches Arvin to wait for the right moment and then settle it",
               "A car pulled over, two men on the ground, a boy watching",
               "Every choice Arvin makes later traces back to this lesson",
               "When does Arvin use it?",
               causes=["arvin_bullied"], chars=["Willard", "Arvin"], role="rule_clarify",
               narration_at=25.0 * M, evidence_at=24.0 * M,
               intervals=[[24.0 * M, 25.2 * M]]),
            ev("charlotte_illness", 27.6 * M, 29.0 * M,
               "Charlotte collapses at home and the diagnosis comes back cancer",
               "A woman on the kitchen floor, her husband running",
               "This is where the praying stops working",
               "How far will Willard go to fix it?",
               causes=["crucified_soldier"], chars=["Charlotte", "Willard"],
               role="causal_bridge", narration_at=28.2 * M, evidence_at=27.6 * M,
               intervals=[[27.6 * M, 28.6 * M]]),
            ev("jack_sacrifice", 29.0 * M, 30.6 * M,
               "Willard sacrifices Arvin's dog at the prayer log",
               "The cross, a man carrying a dog up the hill, his son's face",
               "The moment Arvin stops believing anything his father believes",
               "What is left for the boy?",
               causes=["charlotte_illness"], chars=["Willard", "Arvin"], role="stakes",
               narration_at=30.0 * M, evidence_at=29.0 * M,
               intervals=[[29.0 * M, 30.2 * M]]),
        ],
    },
    {
        "id": "roy_ends",
        "status": "draft",
        "audience_question": "Where does Roy's faith finally stop?",
        "exit_answer": None,
        "next_question": "Where does their child end up?",
        "events": [
            ev("roy_kills_helen", 38.8 * M, 40.6 * M,
               "Roy kills Helen in the woods, then tries to raise her from the dead",
               "Woods, a screwdriver, a body, two men driving away",
               "Faith turns into murder in about a minute",
               "How far does he get?",
               causes=["helen_chooses_roy"], chars=["Roy", "Helen", "Theodore"],
               role="causal_bridge", narration_at=39.8 * M, evidence_at=38.8 * M,
               intervals=[[38.8 * M, 40.2 * M]]),
            ev("roy_meets_carl", 45.4 * M, 47.4 * M,
               "Roy thumbs a ride and gets into Carl and Sandy's car",
               "A highway, a man getting in, a camera on the seat",
               "We can see what he is getting into and he cannot",
               "Why does this couple pick people up?",
               causes=["roy_kills_helen"], chars=["Roy", "Carl", "Sandy"], role="stakes",
               narration_at=46.2 * M, evidence_at=45.4 * M,
               intervals=[[45.4 * M, 46.8 * M]]),
        ],
    },
    {
        "id": "arvin_and_lenora_grow",
        "status": "draft",
        "audience_question": "How do the two orphaned kids grow up?",
        "exit_answer": None,
        "next_question": "Who walks into their lives next?",
        "events": [
            ev("lenora_and_arvin", 42.4 * M, 43.6 * M,
               "A grown Arvin settles it for Lenora when boys go after her",
               "Behind the school, three boys down, Arvin walking her home",
               "His father's rule is running him now",
               "What are these two to each other?",
               causes=["willard_teaches_revenge"], chars=["Arvin", "Lenora"],
               role="causal_bridge", narration_at=43.0 * M, evidence_at=42.4 * M,
               intervals=[[42.4 * M, 43.4 * M]]),
            ev("earskell_gives_pistol", 48.4 * M, 49.8 * M,
               "Uncle Earskell hands Arvin his father's pistol for his birthday",
               "A kitchen table, an old Luger, a boy taking it",
               "Once the gun is on screen the only question is when",
               "Who does that gun end up pointed at?",
               causes=["crucified_soldier"], chars=["Arvin"], role="stakes",
               narration_at=49.0 * M, evidence_at=48.4 * M,
               intervals=[[48.4 * M, 49.6 * M]]),
        ],
    },
    {
        "id": "preacher_arrives",
        "status": "draft",
        "audience_question": "What does the new preacher bring to this town?",
        "exit_answer": None,
        "next_question": "What happens to Lenora?",
        "events": [
            ev("teagardin_arrives", 52.0 * M, 53.2 * M,
               "Preston Teagardin takes over the pulpit",
               "A new preacher at the church, a grandmother cooking to welcome him",
               "One arrival tips the whole town",
               "What kind of man is he?",
               chars=["Preston"], role="orient", entry=True,
               narration_at=52.4 * M, evidence_at=52.0 * M,
               intervals=[[52.0 * M, 53.0 * M]]),
            ev("teagardin_sermon", 55.6 * M, 57.4 * M,
               "Teagardin turns a welcome dinner into a sermon aimed at the room",
               "A preacher standing over a table, chicken livers, faces going stiff",
               "His whole method is in how he talks, so let him talk",
               "Who does that voice get turned on?",
               causes=["teagardin_arrives"], chars=["Preston"], role="none",
               intervals=[[55.8 * M, 57.2 * M]]),
            ev("lenora_groomed", 63.6 * M, 65.4 * M,
               "Teagardin uses counselling to get Lenora alone",
               "A parked car, an empty church, a girl and a preacher",
               "He uses her faith as the way in",
               "What does she think is happening?",
               causes=["teagardin_sermon"], chars=["Preston", "Lenora"],
               role="character_subtext", narration_at=64.4 * M, evidence_at=63.6 * M,
               intervals=[[63.6 * M, 65.0 * M]]),
        ],
    },
    {
        "id": "predators_established",
        "status": "draft",
        "audience_question": "Who is the law here, and who is hunting?",
        "exit_answer": None,
        "next_question": "When do these roads cross Arvin's?",
        "events": [
            ev("carl_method", 68.0 * M, 69.4 * M,
               "Carl's rule for picking hitchhikers gets spelled out",
               "A camera, a highway, another man getting in",
               "Now every ride in this film reads as a countdown",
               "Who is next?",
               causes=["roy_meets_carl"], chars=["Carl", "Sandy"], role="rule_clarify",
               narration_at=68.4 * M, evidence_at=68.0 * M,
               intervals=[[68.0 * M, 69.2 * M]]),
            ev("bodecker_corruption", 72.0 * M, 73.6 * M,
               "Sheriff Bodecker runs the county on bribes and threats",
               "Campaign signs, a diner booth, an envelope changing hands",
               "The law here is not protection, it is another threat",
               "If Arvin gets in trouble, who comes for him?",
               chars=["Bodecker"], role="stakes", entry=True,
               narration_at=72.6 * M, evidence_at=72.0 * M,
               intervals=[[72.0 * M, 73.4 * M]]),
        ],
    },
    {
        "id": "lenora_breaks",
        "status": "draft",
        "audience_question": "How far is Lenora pushed?",
        "exit_answer": None,
        "next_question": "What does Arvin find out?",
        "events": [
            ev("lenora_pregnant", 84.0 * M, 85.6 * M,
               "Lenora tells Teagardin she is pregnant and he turns on her",
               "A car, a preacher facing away, a girl left in it",
               "He makes it her fault and drives off",
               "What is left open to her?",
               causes=["lenora_groomed"], chars=["Lenora", "Preston"],
               role="causal_bridge", narration_at=84.8 * M, evidence_at=84.0 * M,
               intervals=[[84.0 * M, 85.4 * M]]),
            ev("lenora_dies", 88.0 * M, 89.6 * M,
               "Lenora hangs herself, and changes her mind a second too late",
               "A barn, a bucket, a girl who has just realised she was wrong",
               "We are told what she is thinking while it happens",
               "How does Arvin learn the truth?",
               causes=["lenora_pregnant"], chars=["Lenora"], role="reflection",
               narration_at=89.0 * M, evidence_at=88.0 * M,
               intervals=[[88.0 * M, 89.4 * M]]),
            ev("suicide_burial_refused", 91.6 * M, 92.6 * M,
               "Arvin hears the church will not bury a suicide",
               "A kitchen conversation, a boy's face closing",
               "The man who did it is fine, and she is the one shut out",
               "What does Arvin decide?",
               causes=["lenora_dies"], chars=["Arvin"], role="causal_bridge",
               narration_at=92.0 * M, evidence_at=91.6 * M,
               intervals=[[91.6 * M, 92.4 * M]]),
        ],
    },
    {
        "id": "arvin_acts",
        "status": "draft",
        "audience_question": "Who does Arvin use his father's rule on?",
        "exit_answer": None,
        "next_question": "Where does he go after that?",
        "events": [
            ev("arvin_confronts_preacher", 96.0 * M, 98.6 * M,
               "Arvin calls Teagardin out by asking for time as a sinner",
               "An empty church, two men sitting, a pistol",
               "The longest verbal fight in the film, so it plays with nothing over it",
               "What does the preacher admit?",
               causes=["suicide_burial_refused", "earskell_gives_pistol"],
               chars=["Arvin", "Preston"], role="none",
               intervals=[[96.2 * M, 98.4 * M]]),
            ev("preacher_dies", 99.6 * M, 101.0 * M,
               "Talking runs out and Arvin fires",
               "A shot inside a church, a young man leaving fast",
               "The line he cannot walk back",
               "Who starts hunting him now?",
               causes=["arvin_confronts_preacher"], chars=["Arvin", "Preston"],
               role="stakes", narration_at=100.2 * M, evidence_at=99.6 * M,
               intervals=[[99.6 * M, 100.8 * M]]),
        ],
    },
    {
        "id": "roads_converge",
        "status": "draft",
        "audience_question": "Whose car picks up a boy on the run?",
        "exit_answer": None,
        "next_question": "What does the sheriff learn?",
        "events": [
            ev("arvin_rides_with_carl", 106.4 * M, 108.6 * M,
               "On the run, Arvin gets into Carl and Sandy's car",
               "A highway, a boy in the back seat, the car turning off into trees",
               "The rule from earlier means we already know what this ride is",
               "Who moves first?",
               causes=["preacher_dies", "carl_method"], chars=["Arvin", "Carl", "Sandy"],
               role="stakes", narration_at=107.2 * M, evidence_at=106.4 * M,
               intervals=[[106.4 * M, 108.4 * M]]),
            ev("woods_shootout", 109.4 * M, 111.4 * M,
               "In the woods it goes wrong for the couple instead",
               "A clearing, a camera, two guns",
               "The film's two loaded threats finally hit each other",
               "Whose family does this land on?",
               causes=["arvin_rides_with_carl"], chars=["Arvin", "Carl", "Sandy"],
               role="none", intervals=[[109.6 * M, 111.2 * M]]),
            ev("bodecker_learns", 112.0 * M, 113.6 * M,
               "Bodecker learns the two bodies are his sister and her husband",
               "A radio call, a sheriff driving out, a scene in the woods",
               "This stops being police work",
               "Where will he look for Arvin?",
               causes=["woods_shootout", "bodecker_corruption"], chars=["Bodecker"],
               role="causal_bridge", narration_at=112.8 * M, evidence_at=112.0 * M,
               intervals=[[112.0 * M, 113.4 * M]]),
        ],
    },
    {
        "id": "cornered",
        "status": "draft",
        "audience_question": "What is waiting where Arvin goes back to?",
        "exit_answer": None,
        "next_question": None,
        "events": [
            ev("arvin_returns_home", 116.4 * M, 118.4 * M,
               "Arvin walks back to the empty hill he grew up on",
               "A collapsed house and barn, a short exchange with a stranger",
               "He has come back to where it started, which is not an accident",
               "Why here?",
               causes=["woods_shootout"], chars=["Arvin"], role="reflection",
               narration_at=117.2 * M, evidence_at=116.4 * M,
               intervals=[[116.4 * M, 118.2 * M]]),
            ev("arvin_understands_father", 122.3 * M, 123.2 * M,
               "Arvin finally understands his father had no choice either",
               "The rotted prayer log, and his father's face in memory",
               "The one moment he forgives the man who ruined him",
               "Where does that leave him?",
               causes=["jack_sacrifice", "arvin_returns_home"],
               chars=["Arvin", "Willard"], role="reflection",
               narration_at=122.7 * M, evidence_at=122.3 * M,
               intervals=[[122.3 * M, 123.1 * M]]),
            ev("bodecker_calls_him_out", 123.4 * M, 124.6 * M,
               "Bodecker calls his name through the trees",
               "A sheriff with a gun, timber, a young man not moving",
               "Hunter and hunted are finally in the same clearing",
               "Does Arvin come out?",
               causes=["bodecker_learns", "arvin_understands_father"],
               chars=["Bodecker", "Arvin"], role="stakes",
               narration_at=123.9 * M, evidence_at=123.4 * M,
               intervals=[[123.4 * M, 124.5 * M]]),
            ev("standoff", 124.9 * M, 126.17 * M,
               "Both guns up, Arvin offering a photograph as proof and asking him to stand down",
               "Two men facing each other, two barrels, a snapshot in a pocket",
               "The last second this could end with words is running out",
               "Who fires first?",
               causes=["bodecker_calls_him_out"], chars=["Arvin", "Bodecker"],
               role="none", intervals=[[124.9 * M, 126.17 * M]]),
        ],
    },
]

CLOSING = {
    "id": "closing_wrap",
    "status": "draft",
    "audience_question": "What was this story actually about?",
    "exit_answer": None,
    "next_question": None,
    "events": [],
}

# The reference closes on one unbroken 66-second block: theme in a single line, then the
# protagonist read, then the cast, then a viewing note. It works because the title's hook -
# the cast - is only paid off at the very end, which is what holds the viewer there. We take
# that shape and drop what it puts first, the outcome. The wrap plays over quiet moments
# adjacent to scenes already shown rather than the exact same frames, because an edit plan
# may not reuse a source interval twice.
CLOSING["events"] = [
    ev("closing_theme", 31.2 * M, 32.6 * M,
       "One line of theme over a boy walking away from that cross",
       "The log cross, and Arvin's back as he leaves it",
       "Every choice made for good reasons leaves blood behind it, and that is the film",
       "Where do choices like that end?",
       causes=["standoff"], chars=["Arvin", "Willard"], role="reflection",
       narration_at=31.4 * M, evidence_at=31.2 * M,
       intervals=[[31.2 * M, 32.6 * M]], must_show=False, transition="bridge"),
    ev("closing_cast_hook", 101.2 * M, 102.6 * M,
       "The cast promised in the title, finally named",
       "Arvin leaving the church, the other faces still fresh",
       "Tom Holland, Robert Pattinson, Sebastian Stan and Eliza Scanlen in one small film "
       "is the hook",
       "Why did all of them sign up for this one?",
       causes=["closing_theme"], chars=["Arvin"], role="reflection",
       narration_at=101.4 * M, evidence_at=101.2 * M,
       intervals=[[101.2 * M, 102.6 * M]], must_show=False, transition="bridge"),
]
sections.append(CLOSING)

story_map = {
    "schema_version": 1,
    "project_title": "THE DEVIL ALL THE TIME REVIEW",
    "timeline_mode": "audience_reveal",
    "timeline_mode_reason": "The review opens on the prayer log at 22:24 and then rewinds to "
                            "the war, and it groups the film's cross-cut threads by character. "
                            "Neither is chronological in source time.",
    "spoiler_cutoff_source_sec": SPOILER_CUTOFF,
    "review_language": "en",
    "reference_structure": {
        "learned_from": "rd5pF9Qj_C8",
        "note": "Structure only. That review reveals the ending; this map stops before the "
                "shooting.",
        "carried_over": [
            "one character group at a time instead of the film's cross-cutting",
            "single short beats for connective information",
            "the closing confrontations take the largest share",
            "the film's own dialogue left running at the confrontations",
            "an unbroken closing block: theme, then protagonist read, then the cast hook",
            "the cast hook is promised in the title and paid off only at the very end",
        ],
        "deliberately_not_carried": [
            "the outcome. The reference names who dies and who walks away; this map cuts on "
            "the raised guns at 126:10, the last line before the shooting.",
        ],
    },
    "sections": sections,
}

OUT.write_text(json.dumps(story_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

total = sum(b - a for s in sections for e in s["events"] for a, b in e["selected_intervals"])
events = sum(len(s["events"]) for s in sections)
narrated = sum(1 for s in sections for e in s["events"] if e["narration_role"] != "none")
print(f"wrote {OUT.name}")
print(f"  sections {len(sections)}, events {events}")
print(f"  selected {total:.0f}s = {total/60:.1f} min")
print(f"  narrated {narrated}, film dialogue kept {events - narrated}")
print(f"  spoiler cutoff {SPOILER_CUTOFF/60:.1f} min")

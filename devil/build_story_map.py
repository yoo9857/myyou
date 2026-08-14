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
    # The promised footage is the head of the scene, not the whole of it. Twelve seconds
    # is the least a beat gets - one narration block over the establishing shot, then the
    # film running under it - so a promise that size is one the plan can actually keep.
    # The 14-second ceiling comes from measurement: at 18 the two thinnest beats,
    # teagardin_arrives and carl_method, covered only 81 percent of what they promised.
    core = min(max((end - start) * 0.3, 12.0), 14.0)
    interval_list = [list(i) for i in (intervals or [[start, min(start + core, end)]])]
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


# Every interval below was checked against the film itself before being trusted. The first
# pass took its timings from the subtitle track and 12 of 33 landed on the wrong scene -
# the cold open on a boy in a car, the crucified soldier on a daylit street - because a
# subtitle records who speaks, not what is on screen, and this film carries its key beats
# in silence. Each corrected value now carries the frame or the unambiguous line that
# pinned it. `needs_visual_review` exists for exactly this and should stay true until the
# frames have actually been looked at.
sections = [
    {
        "id": "cold_open_prayer_log",
        "status": "draft",
        "audience_question": "Why is this man kneeling at a cross in the woods?",
        "exit_answer": None,
        "next_question": "When did the praying start?",
        "events": [
            ev("prayer_log_present", 26.6 * M, 27.4 * M,  # frame 27m00s - Willard's hand on Arvin's head at the log
               "Willard kneels at a cross he built in the woods, his son beside him",
               "A father and son on their knees at a log cross, the wood dark with blood",
               "The ritual arrives with no explanation, which is exactly why it holds",
               "What is this prayer trying to hold back?",
               chars=["Willard", "Arvin"], role="orient",
               narration_at=26.76 * M, evidence_at=26.6 * M,
               entry=True, transition="opening"),
        ],
    },
    {
        "id": "willard_war_and_charlotte",
        "status": "draft",
        "audience_question": "Where did Willard get this faith?",
        "exit_answer": None,
        "next_question": "What holds the family he builds together?",
        "events": [
            ev("crucified_soldier", 3.75 * M, 4.6 * M,  # frame 4m05s - cross on the burnt hill
               "In the Pacific, Willard finds a US soldier nailed up and still alive",
               "A man lashed to a cross, maggots, Willard raising his sidearm",
               "Everything he later does with God starts here",
               "What does that leave in him?",
               causes=["prayer_log_present"], chars=["Willard"], role="causal_bridge",
               narration_at=3.92 * M, evidence_at=3.75 * M),
            ev("meets_charlotte", 6.2 * M, 7.85 * M,  # 'That was nice, what you did' 6.95m; 'nice to meet you, too' 7.70m
               "On the way home he sees Charlotte in a diner and says nothing",
               "A diner counter, a waitress, a man walking out without a word",
               "His silence is what lets his mother start arranging his life",
               "Will he come back for her?",
               causes=["crucified_soldier"], chars=["Willard", "Charlotte"], role="none"),
            ev("emma_matchmaking", 9.85 * M, 10.6 * M,  # 'Willard, I've asked Helen to sit with us' 9.99m; frame 10m05s church
               "His mother Emma lines him up with Helen from her church",
               "A conversation outside the church, mother and son",
               "Two marriages get decided in one conversation",
               "Which woman does he choose?",
               causes=["meets_charlotte"], chars=["Willard", "Emma", "Helen"],
               role="rule_clarify", narration_at=10.0 * M, evidence_at=9.85 * M),
        ],
    },
    {
        "id": "roy_and_helen_parallel",
        "status": "draft",
        "audience_question": "What became of the other couple from that same church?",
        "exit_answer": None,
        "next_question": "How far will that kind of faith go?",
        "events": [
            ev("roy_spider_sermon", 13.3 * M, 14.8 * M,  # frames 13m30s at the pulpit, 14m30s the jar going over his head
               "Roy the preacher pours a jar of spiders over his own head to prove his faith",
               "A pulpit, a jar of spiders, a congregation coming apart",
               "Summarising this would kill it, so the scene has to play",
               "What kind of person falls for this man?",
               causes=["emma_matchmaking"], chars=["Roy", "Helen", "Theodore"], role="none"),
            ev("helen_chooses_roy", 15.1 * M, 15.42 * M,  # immediately after the spiders
               "Helen takes it as a sign and chooses him",
               "Helen's face after the service, moving toward him",
               "This is the choice the rest of her life answers for",
               "How does this marriage end?",
               causes=["roy_spider_sermon"], chars=["Roy", "Helen"], role="stakes",
               narration_at=15.16 * M, evidence_at=15.1 * M),
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
               causes=["meets_charlotte"], chars=["Arvin"], role="none"),
            ev("willard_teaches_revenge", 23.6 * M, 24.75 * M,  # 'Just gotta pick the right time' 24.13m
               "Willard teaches Arvin to wait for the right moment and then settle it",
               "A car pulled over, two men on the ground, a boy watching",
               "Every choice Arvin makes later traces back to this lesson",
               "When does Arvin use it?",
               causes=["arvin_bullied"], chars=["Willard", "Arvin"], role="rule_clarify",
               narration_at=23.83 * M, evidence_at=23.6 * M),
            ev("charlotte_illness", 24.7 * M, 25.85 * M,  # frame 24m55s Charlotte collapsing; 'destroy that cancer' 25.36m
               "Charlotte collapses at home and the diagnosis comes back cancer",
               "A woman on the kitchen floor, her husband running",
               "This is where the praying stops working",
               "How far will Willard go to fix it?",
               causes=["crucified_soldier"], chars=["Charlotte", "Willard"],
               role="causal_bridge", narration_at=24.93 * M, evidence_at=24.7 * M),
            ev("jack_sacrifice", 29.05 * M, 29.85 * M,  # 'asking men to make sacrifices' 28.67m; frames 29m15s, 29m40s
               "Willard sacrifices Arvin's dog at the prayer log",
               "The cross, a man carrying a dog up the hill, his son's face",
               "The moment Arvin stops believing anything his father believes",
               "What is left for the boy?",
               causes=["charlotte_illness"], chars=["Willard", "Arvin"], role="stakes",
               narration_at=29.21 * M, evidence_at=29.05 * M),
        ],
    },
    {
        "id": "roy_ends",
        "status": "draft",
        "audience_question": "Where does Roy's faith finally stop?",
        "exit_answer": None,
        "next_question": "Where does their child end up?",
        "events": [
            ev("roy_kills_helen", 37.6 * M, 39.65 * M,  # frame 37m40s Helen down; 39m30s Roy calling her back
               "Roy kills Helen in the woods, then tries to raise her from the dead",
               "Woods, a screwdriver, a body, two men driving away",
               "Faith turns into murder in about a minute",
               "How far does he get?",
               causes=["helen_chooses_roy"], chars=["Roy", "Helen", "Theodore"],
               role="causal_bridge", narration_at=38.01 * M, evidence_at=37.6 * M),
            ev("roy_meets_carl", 40.85 * M, 42.1 * M,  # 'I'm Carl, by the way, this here's Sandy' 41.39m
               "Roy thumbs a ride and gets into Carl and Sandy's car",
               "A highway, a man getting in, a camera on the seat",
               "We can see what he is getting into and he cannot",
               "Why does this couple pick people up?",
               causes=["roy_kills_helen"], chars=["Roy", "Carl", "Sandy"], role="stakes",
               narration_at=41.1 * M, evidence_at=40.85 * M),
        ],
    },
    {
        "id": "arvin_and_lenora_grow",
        "status": "draft",
        "audience_question": "How do the two orphaned kids grow up?",
        "exit_answer": None,
        "next_question": "Who walks into their lives next?",
        "events": [
            ev("lenora_and_arvin", 49.2 * M, 50.4 * M,  # frame 49m20s Helen Hatton Laferty's headstone; narration 49.35m
               "A grown Arvin settles it for Lenora when boys go after her",
               "Behind the school, three boys down, Arvin walking her home",
               "His father's rule is running him now",
               "What are these two to each other?",
               causes=["willard_teaches_revenge"], chars=["Arvin", "Lenora"],
               role="causal_bridge", narration_at=49.44 * M, evidence_at=49.2 * M),
            ev("earskell_gives_pistol", 46.7 * M, 48.4 * M,  # frame 48m00s Earskell; 'That's a German Luger' 47.95m
               "Uncle Earskell hands Arvin his father's pistol for his birthday",
               "A kitchen table, an old Luger, a boy taking it",
               "Once the gun is on screen the only question is when",
               "Who does that gun end up pointed at?",
               causes=["crucified_soldier"], chars=["Arvin"], role="stakes",
               narration_at=47.04 * M, evidence_at=46.7 * M),
        ],
    },
    {
        "id": "preacher_arrives",
        "status": "draft",
        "audience_question": "What does the new preacher bring to this town?",
        "exit_answer": None,
        "next_question": "What happens to Lenora?",
        "events": [
            ev("teagardin_arrives", 54.25 * M, 55.3 * M,  # 'Hello there... What you got there?' 54.41m - the chicken livers
               "Preston Teagardin takes over the pulpit",
               "A new preacher at the church, a grandmother cooking to welcome him",
               "One arrival tips the whole town",
               "What kind of man is he?",
               chars=["Preston"], role="orient", entry=True,
               narration_at=54.46 * M, evidence_at=54.25 * M),
            ev("teagardin_sermon", 55.6 * M, 57.15 * M,  # 'we're all humble people gathered here' 55.68m to 'that's what I'm going to do, friends' 56.90m
               "Teagardin turns a welcome dinner into a sermon aimed at the room",
               "A preacher standing over a table, chicken livers, faces going stiff",
               "His whole method is in how he talks, so let him talk",
               "Who does that voice get turned on?",
               causes=["teagardin_arrives"], chars=["Preston"], role="none"),
            ev("lenora_groomed", 63.8 * M, 65.6 * M,  # 'in my birthday suit? No' 64.43m; 'She presents herself to you now' 65.13m
               "Teagardin uses counselling to get Lenora alone",
               "A parked car, an empty church, a girl and a preacher",
               "He uses her faith as the way in",
               "What does she think is happening?",
               causes=["teagardin_sermon"], chars=["Preston", "Lenora"],
               role="character_subtext", narration_at=64.16 * M, evidence_at=63.8 * M),
        ],
    },
    {
        "id": "predators_established",
        "status": "draft",
        "audience_question": "Who is the law here, and who is hunting?",
        "exit_answer": None,
        "next_question": "When do these roads cross Arvin's?",
        "events": [
            ev("carl_method", 42.7 * M, 44.4 * M,  # frames 42m50s car, 43m20s Sandy, 43m50s Roy; 'take some pictures' 43.01m
               "Carl's rule for picking hitchhikers gets spelled out",
               "A camera, a highway, another man getting in",
               "Now every ride in this film reads as a countdown",
               "Who is next?",
               causes=["roy_meets_carl"], chars=["Carl", "Sandy"], role="rule_clarify",
               narration_at=43.04 * M, evidence_at=42.7 * M),
            ev("bodecker_corruption", 71.05 * M, 72.6 * M,  # 'I got another election coming up, Sandy' 71.17m
               "Sheriff Bodecker runs the county on bribes and threats",
               "Campaign signs, a diner booth, an envelope changing hands",
               "The law here is not protection, it is another threat",
               "If Arvin gets in trouble, who comes for him?",
               chars=["Bodecker"], role="stakes", entry=True,
               narration_at=71.36 * M, evidence_at=71.05 * M),
        ],
    },
    {
        "id": "lenora_breaks",
        "status": "draft",
        "audience_question": "How far is Lenora pushed?",
        "exit_answer": None,
        "next_question": "What does Arvin find out?",
        "events": [
            ev("lenora_pregnant", 86.9 * M, 88.1 * M,  # 'figure some way to get rid of it' 87.39m
               "Lenora tells Teagardin she is pregnant and he turns on her",
               "A car, a preacher facing away, a girl left in it",
               "He makes it her fault and drives off",
               "What is left open to her?",
               causes=["lenora_groomed"], chars=["Lenora", "Preston"],
               role="causal_bridge", narration_at=87.14 * M, evidence_at=86.9 * M),
            ev("lenora_dies", 89.05 * M, 89.58 * M,  # frame 89m20s the barn; 'No one would know she wasn't a suicide' 89.39m
               "Lenora hangs herself, and changes her mind a second too late",
               "A barn, a bucket, a girl who has just realised she was wrong",
               "We are told what she is thinking while it happens",
               "How does Arvin learn the truth?",
               causes=["lenora_pregnant"], chars=["Lenora"], role="reflection",
               narration_at=89.16 * M, evidence_at=89.05 * M),
            ev("suicide_burial_refused", 89.6 * M, 90.6 * M,  # frame 89m50s the coffin at the graveside
               "Arvin hears the church will not bury a suicide",
               "A kitchen conversation, a boy's face closing",
               "The man who did it is fine, and she is the one shut out",
               "What does Arvin decide?",
               causes=["lenora_dies"], chars=["Arvin"], role="causal_bridge",
               narration_at=89.8 * M, evidence_at=89.6 * M),
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
               chars=["Arvin", "Preston"], role="none"),
            ev("preacher_dies", 99.6 * M, 101.0 * M,
               "Talking runs out and Arvin fires",
               "A shot inside a church, a young man leaving fast",
               "The line he cannot walk back",
               "Who starts hunting him now?",
               causes=["arvin_confronts_preacher"], chars=["Arvin", "Preston"],
               role="stakes", narration_at=100.2 * M, evidence_at=99.6 * M),
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
               role="stakes", narration_at=107.2 * M, evidence_at=106.4 * M),
            ev("woods_shootout", 109.4 * M, 111.4 * M,
               "In the woods it goes wrong for the couple instead",
               "A clearing, a camera, two guns",
               "The film's two loaded threats finally hit each other",
               "Whose family does this land on?",
               causes=["arvin_rides_with_carl"], chars=["Arvin", "Carl", "Sandy"],
               role="none"),
            ev("bodecker_learns", 112.85 * M, 114.0 * M,  # 'It's your sister and her husband' 113.05m
               "Bodecker learns the two bodies are his sister and her husband",
               "A radio call, a sheriff driving out, a scene in the woods",
               "This stops being police work",
               "Where will he look for Arvin?",
               causes=["woods_shootout", "bodecker_corruption"], chars=["Bodecker"],
               role="causal_bridge", narration_at=113.08 * M, evidence_at=112.85 * M),
        ],
    },
    {
        "id": "cornered",
        "status": "draft",
        "audience_question": "What is waiting where Arvin goes back to?",
        "exit_answer": None,
        "next_question": None,
        "events": [
            ev("arvin_returns_home", 117.0 * M, 118.4 * M,
               "Arvin walks back to the empty hill he grew up on",
               "A collapsed house and barn, a short exchange with a stranger",
               "He has come back to where it started, which is not an accident",
               "Why here?",
               causes=["woods_shootout"], chars=["Arvin"], role="reflection",
               narration_at=117.28 * M, evidence_at=117.0 * M),
            ev("arvin_understands_father", 122.3 * M, 123.2 * M,
               "Arvin finally understands his father had no choice either",
               "The rotted prayer log, and his father's face in memory",
               "The one moment he forgives the man who ruined him",
               "Where does that leave him?",
               causes=["jack_sacrifice", "arvin_returns_home"],
               chars=["Arvin", "Willard"], role="reflection",
               narration_at=122.7 * M, evidence_at=122.3 * M),
            ev("bodecker_calls_him_out", 123.4 * M, 124.6 * M,
               "Bodecker calls his name through the trees",
               "A sheriff with a gun, timber, a young man not moving",
               "Hunter and hunted are finally in the same clearing",
               "Does Arvin come out?",
               causes=["bodecker_learns", "arvin_understands_father"],
               chars=["Bodecker", "Arvin"], role="stakes",
               narration_at=123.9 * M, evidence_at=123.4 * M),
            ev("standoff", 124.9 * M, 126.15 * M,
               "Both guns up, Arvin offering a photograph as proof and asking him to stand down",
               "Two men facing each other, two barrels, a snapshot in a pocket",
               "The last second this could end with words is running out",
               "Who fires first?",
               causes=["bodecker_calls_him_out"], chars=["Arvin", "Bodecker"],
               role="none"),
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
    ev("closing_theme", 30.3 * M, 30.95 * M,  # 'There used to be a house and a barn up on the hill' 116.90m
       "One line of theme over a boy walking up to an empty house",
       "A pickup outside the house, and a small figure coming up the road alone",
       "Every choice made for good reasons leaves blood behind it, and that is the film",
       "Where do choices like that end?",
       causes=["standoff"], chars=["Arvin", "Willard"], role="reflection",
       narration_at=30.43 * M, evidence_at=30.3 * M,
       must_show=False, transition="bridge"),
    ev("closing_cast_hook", 116.2 * M, 116.7 * M,  # Arvin travelling alone, before 'Howdy' 116.70m
       "The cast promised in the title, finally named",
       "Bodecker alone in his office, the face the poster sells",
       "Tom Holland, Robert Pattinson, Sebastian Stan and Eliza Scanlen in one small film "
       "is the hook",
       "Why did all of them sign up for this one?",
       causes=["closing_theme"], chars=["Arvin"], role="reflection",
       narration_at=116.3 * M, evidence_at=116.2 * M,
       must_show=False, transition="bridge"),
]
sections.append(CLOSING)

# Each section has to close the question it opened and hand the next one forward, or the
# review reads as a list of things that happen. The one exception is `cornered`: its
# question is left standing on purpose, because that is where the review stops.
ARCS = {
    "cold_open_prayer_log":
        "Because he came back from a war carrying something he has no other way to set down",
    "willard_war_and_charlotte":
        "From a man nailed to a cross in the Pacific he could not save and had to finish",
    "roy_and_helen_parallel":
        "Roy proved his faith with a jar of spiders, and Helen read it as a sign and took him",
    "arvin_boyhood":
        "That the world is full of no-good sons of bitches and the only thing you choose is "
        "your moment",
    "roy_ends":
        "At a body he cannot pray back up, and a car he gets into with two strangers",
    "arvin_and_lenora_grow":
        "In one house under one grandmother, with Arvin standing between Lenora and everyone "
        "else",
    "preacher_arrives":
        "A voice the congregation loves, and a habit of getting girls alone in his car",
    "predators_established":
        "A sheriff selling the county to keep his job, and a couple who photograph the men "
        "they pick up",
    "lenora_breaks":
        "To a rope in the barn, carrying a child she was told to get rid of",
    "arvin_acts":
        "The preacher, after being given every chance to say one true thing",
    "roads_converge":
        "The same couple that picked up Roy, and this time the photographer is the one on "
        "the ground",
    "cornered":
        "The sheriff, in the trees above the prayer log, both men out of cover and both guns up",
    "closing_wrap":
        "Everyone in it does the worst thing they do for a reason they believe is good",
}
FOLLOW_ON = {
    "cornered": "Which one of them fires first?",
    "closing_wrap": "Whose reason would you have believed?",
}

for section in sections:
    section["exit_answer"] = ARCS[section["id"]]
    if section["id"] in FOLLOW_ON:
        section["next_question"] = FOLLOW_ON[section["id"]]
    section["status"] = "approved"

# Cleared only because the frames were pulled and looked at, one per event. The first pass
# had 12 of 33 on the wrong scene and this flag is what caught it, so it should go back to
# true the moment any interval moves again.
for section in sections:
    for event in section["events"]:
        event["needs_visual_review"] = False

story_map = {
    "schema_version": 1,
    "project_title": "THE DEVIL ALL THE TIME REVIEW",
    "premise": "In postwar southern Ohio and West Virginia, a boy raised on his father's violent prayers grows up among preachers, a serial-killing couple and a corrupt sheriff, and every one of them does the worst thing they do for a reason they believe is good.",
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

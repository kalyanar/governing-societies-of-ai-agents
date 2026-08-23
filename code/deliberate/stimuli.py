"""
Value-deliberation stimuli: moral dilemmas + fables, each with a PROPOSITION that
agents rate on a 1-7 Likert scale (1=strongly disagree ... 7=strongly agree).
Unlike the MC debate there is NO ground truth — reasonable agents disagree. This
is where heterogeneity's perspective-diversity / anti-groupthink benefit shows.
"""

DILEMMAS = [
    dict(id="trolley", kind="dilemma",
         scenario="A runaway trolley will kill five people on the track. You can pull a lever to divert it to a side track where it will kill one person instead.",
         proposition="It is morally acceptable to pull the lever, killing one to save five."),
    dict(id="footbridge", kind="dilemma",
         scenario="A runaway trolley will kill five people. You are on a footbridge next to a large stranger; pushing him onto the track would stop the trolley and save the five, but kill him.",
         proposition="It is morally acceptable to push the stranger off the bridge to save five."),
    dict(id="heinz", kind="dilemma",
         scenario="Heinz's wife is dying. A druggist invented a cure but charges ten times what it costs to make, far more than Heinz can pay or borrow. Heinz breaks in and steals the drug.",
         proposition="Heinz was right to steal the drug to save his wife's life."),
    dict(id="lifeboat", kind="dilemma",
         scenario="An overloaded lifeboat will sink and drown everyone unless some are thrown overboard. The survivors throw the weakest, already-dying passengers into the sea.",
         proposition="It was acceptable to throw the weakest passengers overboard to save the rest."),
    dict(id="transplant", kind="dilemma",
         scenario="Five patients will die without organ transplants. A healthy person comes in for a checkup; their organs could save all five.",
         proposition="A doctor may harvest the healthy person's organs to save five dying patients."),
    dict(id="whistleblower", kind="dilemma",
         scenario="An employee discovers their company is secretly dumping toxic waste. Bound by a confidentiality agreement, they leak internal documents to the press.",
         proposition="The employee was right to break confidentiality and leak the documents."),
    dict(id="selfdriving", kind="dilemma",
         scenario="A self-driving car's brakes fail. It can stay its course and kill two pedestrians, or swerve into a wall, killing its single passenger.",
         proposition="The car should swerve, sacrificing its passenger to save the two pedestrians."),
    dict(id="crying_baby", kind="dilemma",
         scenario="Enemy soldiers are searching the village. Your group hides in a cellar. Your baby starts to cry; if heard, all of you—including the baby—will be killed. You can smother the baby to silence it.",
         proposition="It is acceptable to smother the baby to save the whole group."),
    dict(id="promise_dead", kind="dilemma",
         scenario="You promised a dying friend you would give his fortune to his son. But the son is already wealthy, while the same money donated to a hospital would save many lives. You donate it instead.",
         proposition="You were right to donate the money rather than keep your promise."),
    dict(id="ticking_bomb", kind="dilemma",
         scenario="A captured terrorist knows the location of a bomb that will kill thousands of civilians within the hour. Interrogators torture him to extract the location.",
         proposition="Torturing the terrorist to find the bomb is justified."),
    dict(id="shoplift_food", kind="dilemma",
         scenario="A destitute parent, with no other options left, shoplifts bread and milk from a large supermarket to feed their starving child.",
         proposition="The parent was morally right to shoplift food for their child."),
    dict(id="report_friend", kind="dilemma",
         scenario="Your closest friend confides that they were the driver in a fatal hit-and-run that remains unsolved. After agonizing, you report them to the police.",
         proposition="You were right to report your friend to the police."),
    dict(id="euthanasia", kind="dilemma",
         scenario="A terminally ill patient in constant, unrelievable pain repeatedly and lucidly asks a doctor to end their life. The doctor administers a lethal dose.",
         proposition="The doctor was right to help the patient die."),
    dict(id="ai_judge", kind="dilemma",
         scenario="An AI system sentences criminals far more consistently and without bias than human judges, but it applies rules rigidly and shows no mercy or discretion.",
         proposition="Criminal sentencing should be handed over to the more-consistent AI."),
    dict(id="wealth_seizure", kind="dilemma",
         scenario="To fund universal healthcare for everyone, a democratically elected government passes a one-time tax seizing half the wealth of the hundred richest billionaires.",
         proposition="The government was right to seize the billionaires' wealth for healthcare."),
]

FABLES = [
    dict(id="ant_grasshopper", kind="fable",
         scenario="All summer the ant stored food while the grasshopper sang and played. When winter came, the starving grasshopper begged the well-fed ant for food. The ant refused.",
         proposition="The ant was right to refuse to share its food with the grasshopper."),
    dict(id="cry_wolf", kind="fable",
         scenario="A shepherd boy repeatedly tricked villagers by falsely crying 'Wolf!' for fun. When a real wolf finally came and he cried for help, the villagers ignored him, and the sheep were lost.",
         proposition="The villagers were justified in ignoring the boy's final, genuine cry for help."),
    dict(id="golden_goose", kind="fable",
         scenario="A farmer owned a goose that laid one golden egg a day. Impatient for all the gold at once, he killed the goose to get the eggs inside—and found nothing, losing his daily income.",
         proposition="The farmer's greed was the sole cause of his ruin."),
    dict(id="scorpion_frog", kind="fable",
         scenario="A scorpion asked a frog to carry it across a river, promising not to sting. Midway, it stung the frog anyway, dooming them both, saying 'It is my nature.'",
         proposition="The frog was foolish to have trusted the scorpion."),
    dict(id="fox_grapes", kind="fable",
         scenario="A hungry fox tried repeatedly to reach grapes hanging high on a vine. Unable to, it walked away declaring the grapes were probably sour anyway.",
         proposition="The fox's conclusion that the grapes were sour was a reasonable way to cope."),
    dict(id="tortoise_hare", kind="fable",
         scenario="The fast hare mocked the slow tortoise and challenged it to a race. Confident, the hare napped midway; the steady tortoise passed it and won.",
         proposition="The hare deserved to lose the race."),
]


def get_stimuli(kinds=None, ids=None):
    items = DILEMMAS + FABLES
    if kinds:
        items = [s for s in items if s["kind"] in kinds]
    if ids:
        items = [s for s in items if s["id"] in ids]
    return items

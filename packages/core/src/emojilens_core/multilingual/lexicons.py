"""Seed function-word lexicons for Latin-script language-variety identification.

Curated by hand for EmojiLens (v0.1) from common function words and high-frequency
chat vocabulary. These lists are a transparent heuristic baseline, not a validated
language-ID model. Words spelled the same in several varieties (e.g. "to", "ke") are
counted fractionally across all of them, never assigned to one by guesswork.

Limitation: Romanized Gujarati has no standard orthography and little public data,
so its lexicon is the smallest and least reliable (see research/LIMITATIONS.md).
"""

from __future__ import annotations

LEXICON_VERSION = "0.1.0"

EN = frozenset(
    """
    the is are was were be been being have has had do does did will would can could should
    shall may might must a an and or but if of in on at by for with about from into over
    under this that these those it its i you he she we they me him her us them my your his
    our their what which who whom when where why how not no yes all some any there here very
    just so than then now today tonight tomorrow yesterday please thanks thank hello good
    great nice see get got go going gone know like want need time day party love happy sorry
    okay ok really well also only even still because been again soon later meet let lets
    """.split()
)

HI_LATN = frozenset(
    """
    hai hain nahi nahin nhi kya kyun kyu kyon aur bhi mein mujhe mera meri mere tera teri
    tere tum tu aap hum ham yeh ye woh vo kaise kaisa kaisi kab kahan kal aaj abhi accha
    acha achha theek thik bahut bohot bahot bhai yaar kuch sab koi karna karo kar raha rahi
    rahe gaya gayi tha thi ho hoga hogi sakta sakti sakte chahiye matlab lekin phir fir wala
    wali wale ke ka ki ko se pe toh to na haan ji milte chalo pata kyunki isliye bas dekho
    bolo suno mat jaldi dost ghar khana pyaar zindagi dil baat batao hua hui kaun kitna
    """.split()
)

GU_LATN = frozenset(
    """
    che chhe nathi nai kem shu su tame tamne tamaru tamari tamara maru mari mara mane amne
    ame aapne hu kyare kya kyan ahiya ahi tya pan ane ke to aavjo aavo jao jaiye chalo saru
    saras majama maja mast bau bahu khub thayu thay karvu kariye joiye joie hatu hati hato
    chhu chu cho chho haji kai kaik badhu badha ghare aaje kale jamva jamvanu avsho evu aavu
    jevu etlu ketlu kevi kevu sha mate mathi nu ni na thi kharekhar bhai ben mummy pappa
    """.split()
)

LEXICONS: dict[str, frozenset[str]] = {"en": EN, "hi-Latn": HI_LATN, "gu-Latn": GU_LATN}

"""First-run content so the website is never empty.

* Doctors use the names and portraits already on the clinic site. Credentials are left EMPTY on purpose:
  nothing is invented. Staff fill them in under /admin > Doctors (the profile checklist shows what is missing).
* Condition pages are general patient information written as a starting point. Staff should have a doctor
  review them, then pick that doctor under "Medically reviewed by". The site only shows the reviewer once chosen.
* Reviews and blog posts are clearly marked SAMPLE and appear with a "Sample" label until staff replace them.
  Set SEED_SAMPLE_CONTENT=0 to skip them entirely.
"""
from datetime import datetime, timedelta

from .clinic_data import DOCTORS
from .models import utcnow
from .content_models import Condition, Doctor, Review, db

DOCTOR_ROLE = "Dermatology team"

CONDITIONS = [
    dict(
        slug="acne", name="Acne", image="services/common-conditions.jpg",
        summary="Blocked pores and inflamed spots, most often on the face, chest and back. Acne is very common and treatable at any age.",
        facts="Main signs | Blackheads, whiteheads and red or painful spots\nCommon areas | Face, chest and back\nOften starts | In the teenage years, but can appear at any age\nSee a doctor if | Lumps are deep or painful, or marks and scars are forming",
        symptoms="Blackheads and whiteheads\nRed, swollen spots (papules and pustules)\nDeep, painful lumps (nodules and cysts)\nDark marks or scars after spots heal",
        causes="Acne starts when oil and dead skin cells block hair follicles. Bacteria on the skin and inflammation then turn the blockage into a spot. Hormone changes, some medicines, stress and family history can make acne more likely or worse. Picking at spots raises the risk of scarring.",
        steps="Skin assessment | Your dermatologist looks at your skin type, the kind of spots you have and what you have already tried.\nTreatment plan | Creams, gels or tablets are matched to how severe your acne is and how your skin reacts.\nFollow-up and scars | Progress is reviewed and the plan adjusted. Treatments for marks and scars can be added once the skin is calm.",
        faqs="Does acne go away on its own? | Mild acne often improves with age, but moderate and severe acne usually needs treatment to prevent scarring.\nCan I start with an online visit? | Yes. An online visit with clear photos suits assessment and follow-ups. Procedures are done in the clinic.\nHow long until I see results? | Most treatments take several weeks. Your doctor will tell you what to expect for your plan."),
    dict(
        slug="vitiligo", name="Vitiligo", image="services/pigment.jpg",
        summary="Patches of skin lose their colour. Vitiligo is not contagious, and treatment can help restore pigment or slow spread.",
        facts="Main sign | Pale or white patches of skin\nCommon areas | Hands, face, and around the eyes and mouth\nWorse in sun | Patches show up more on tanned skin\nSee a doctor if | Patches spread or appear on the face",
        symptoms="Light or white patches that grow slowly or suddenly\nHair in the affected area turning white\nPatches that are more visible after sun exposure\nUsually no pain or itch",
        causes="Vitiligo happens when the cells that make skin colour stop working. It is linked to the immune system, and family history or other autoimmune conditions can play a role. A dermatologist can confirm the diagnosis and rule out look-alike conditions.",
        steps="Diagnosis | Your dermatologist examines the patches and checks for related conditions.\nTreatment plan | Options can include prescription creams and light-based treatments such as phototherapy, chosen for the area and how stable the patches are.\nLong-term follow-up | Repigmentation takes time, so progress is reviewed regularly and the plan adjusted.",
        faqs="Is vitiligo contagious? | No. It cannot be passed from one person to another.\nCan the colour come back? | Often partly or fully, especially with early treatment and consistency. Your doctor will set realistic expectations.\nCan I start with a video consultation? | Yes. Assessment and follow-ups work well online. Light-based sessions happen in the clinic."),
    dict(
        slug="psoriasis", name="Psoriasis", image="about.jpg",
        summary="A long-term skin condition that causes raised, scaly patches. Flare-ups come and go, and good treatment keeps them under control.",
        facts="Main signs | Raised red patches with silvery scales\nCommon areas | Elbows, knees, scalp and lower back\nPattern | Flares and quiet periods\nSee a doctor if | Patches spread, crack, or joints become stiff and painful",
        symptoms="Thick, red or dark patches covered in scales\nDry, cracked skin that may bleed\nItching or soreness\nPitted or thickened nails",
        causes="Psoriasis is driven by an overactive immune system that speeds up skin cell growth. It runs in families. Stress, skin injury, infections and some medicines can trigger flare-ups.",
        steps="Assessment | Your dermatologist checks the skin, scalp, nails and joints and asks about triggers.\nTreatment plan | Creams, light therapy or tablets are chosen for how much skin is affected and how you respond.\nOngoing care | Regular reviews help prevent flare-ups and protect joints and nails.",
        faqs="Is psoriasis contagious? | No.\nIs there a cure? | There is no cure, but treatment can clear or greatly reduce symptoms for long periods.\nCan stress make it worse? | Yes, stress is a common trigger. Your doctor can help you plan around it."),
    dict(
        slug="skin-cancer-screening", name="Skin cancer screening", image="services/cancer-screening.jpg",
        summary="A careful check of your skin and moles to find skin cancer early, when it is easiest to treat.",
        facts="Who should check | Anyone with a new, changing or unusual mole or spot\nWhat we look at | Moles, spots, nails and hard-to-see areas\nWarning signs | Changes in size, shape, colour or bleeding\nSee a doctor if | A spot is new, changing, bleeding or does not heal",
        symptoms="A mole that changes in size, shape or colour\nA sore that does not heal\nA new spot that looks different from others\nBleeding, crusting or itching in a mole",
        causes="Most skin cancers are linked to ultraviolet (UV) exposure from the sun over many years. Fair skin, many moles, a family history and a weakened immune system raise the risk, but skin cancer can affect any skin tone, often on the palms, soles and nails.",
        steps="Skin check | Your dermatologist examines your skin and moles, often with a hand-held magnifier (dermoscope).\nBiopsy if needed | A small sample of any suspicious spot may be taken for testing.\nTreatment and follow-up | If treatment is needed it is planned with you, and regular checks continue afterwards.",
        faqs="How often should I be checked? | Your dermatologist will advise based on your risk. Checking your own skin monthly is also helpful.\nIs the check painful? | No. A skin check is painless. A biopsy uses a local anaesthetic.\nCan I begin online? | You can ask about a specific spot online with clear photos, but a full-body check and any biopsy happen in the clinic."),
    dict(
        slug="hair-loss", name="Hair loss", image="services/hair-nail.jpg",
        summary="Shedding, thinning or bald patches. Finding the cause is the first step to the right treatment.",
        facts="Common types | Pattern thinning, patchy loss, shedding after illness\nCommon areas | Crown, hairline, or patches anywhere on the scalp\nUseful to note | When it started and any recent illness or stress\nSee a doctor if | Loss is sudden, patchy, or comes with itching or pain",
        symptoms="Gradual thinning on the crown or hairline\nRound bald patches\nMore hair than usual on the pillow or in the brush\nScalp itching, scaling or redness",
        causes="Hair loss has many causes: inherited pattern hair loss, hormone changes, illness, low iron or other nutrient levels, stress, some medicines, scalp conditions and autoimmune conditions. Some causes are temporary and the hair grows back.",
        steps="History and scalp check | Your dermatologist looks at your scalp and hair and may suggest blood tests.\nTreatment plan | Treatment depends on the cause and can include medicines for the scalp or in-clinic treatments such as PRP.\nFollow-up | Hair growth is slow, so progress is checked over several months.",
        faqs="Will my hair grow back? | It depends on the cause. Many types improve with the right treatment.\nWhat is PRP? | Platelet-rich plasma uses a concentrate from your own blood, injected into the scalp to support hair follicles. It is done in the clinic.\nCan I start with an online visit? | Yes, for assessment and follow-ups."),
    dict(
        slug="eczema-dermatitis", name="Eczema and dermatitis", image="services/scar-revision.jpg",
        summary="Dry, itchy, inflamed skin that often flares up. Everyday skin care and the right treatment make a big difference.",
        facts="Main signs | Dry, itchy, red or darker patches\nCommon areas | Folds of elbows and knees, hands, face and neck\nOften starts | In childhood, but can begin at any age\nSee a doctor if | Skin is weeping, infected, or sleep is disturbed by itching",
        symptoms="Intense itching, often worse at night\nDry, rough or scaly skin\nRed, brown or grey patches\nSkin that cracks, weeps or crusts when scratched",
        causes="Eczema is linked to a weakened skin barrier and an overactive immune response. It often runs in families with asthma or hay fever. Soaps, fragrances, heat, sweat, stress and some fabrics can trigger flares. Contact dermatitis is caused by touching an irritant or allergen.",
        steps="Assessment | Your dermatologist identifies the type of eczema and what sets it off.\nTreatment plan | Moisturisers, anti-inflammatory creams and trigger avoidance are the foundation, with other options if needed.\nFollow-up | Plans are adjusted as the skin changes, including for children as they grow.",
        faqs="Is eczema contagious? | No.\nHow do I care for my child's eczema? | Gentle cleansing, regular moisturising and avoiding known triggers help. Your doctor will give a plan for your child.\nCan I start online? | Yes. Photos help your doctor assess flares and adjust treatment."),
]

REVIEWS = [
    dict(condition="vitiligo", treatment="Light therapy", doctor="dagmawit-mitku", rating=5, label="Woman, 30s", symptom="White patches",
         body="The patches on my hands have visibly repigmented after eight months. Every step of the treatment plan was explained clearly."),
    dict(condition="acne", treatment="Prescription treatment", doctor="zina-ahmed", rating=5, label="Man, 20s", symptom="Breakouts",
         body="Years of breakouts finally under control. The follow-up by video call saved me a long trip across the city."),
    dict(condition="psoriasis", treatment="Light therapy", doctor="solomon-worku", rating=4, label="Woman, 40s", symptom="Scaly patches",
         body="Flare-ups are much less frequent. The team is patient and always answers questions without rushing."),
    dict(condition="skin-cancer-screening", treatment="Skin check", doctor="elias-mulat", rating=5, label="Man, 50s", symptom="Changing mole",
         body="A thorough check and a clear explanation of what to watch for. I felt well looked after from start to finish."),
    dict(condition="hair-loss", treatment="PRP", doctor="hiwot-engida", rating=5, label="Woman, 30s", symptom="Hair shedding",
         body="My shedding has slowed and new growth is visible. Honest advice about what to expect."),
    dict(condition="eczema-dermatitis", treatment="Medical treatment", doctor="zina-ahmed", rating=5, label="Child, 8 (parent)", symptom="Itching",
         body="Our daughter sleeps through the night now. The doctor was gentle and great with her."),
]


def seed_content(app):
    sample = app.config.get("SEED_SAMPLE_CONTENT", True)
    if Doctor.query.count() == 0:
        for i, d in enumerate(DOCTORS):
            db.session.add(Doctor(slug=d["slug"], name=d["name"], title=DOCTOR_ROLE, sort_order=(i + 1) * 10,
                                  languages="", accepts_telemedicine=True, published=True, show_on_home=True))
        db.session.commit()
    if Condition.query.count() == 0:
        for i, c in enumerate(CONDITIONS):
            db.session.add(Condition(sort_order=(i + 1) * 10, **c))
        db.session.commit()
    if not sample:
        return
    docs = {d.slug: d for d in Doctor.query.all()}
    conds = {c.slug: c for c in Condition.query.all()}
    if Review.query.count() == 0:
        now = utcnow()
        for i, r in enumerate(REVIEWS):
            db.session.add(Review(condition=conds.get(r["condition"]), doctor=docs.get(r["doctor"]), treatment=r["treatment"],
                                  symptom=r["symptom"], body=r["body"], rating=r["rating"], reviewer_label=r["label"],
                                  consent=True, status="approved", is_sample=True, created_at=now - timedelta(days=3 + i * 9)))
        db.session.commit()


def import_legacy_doctors():
    """One-time: bring over doctors edited in the earlier version of the admin (table 'doctors').

    Their uploaded photo, name and role are copied onto the matching new profile (same slug), and
    any extra doctor staff had added becomes a new profile. Runs once; a Setting row records that.
    """
    from sqlalchemy import text
    from .content_models import Setting, unique_slug
    from .models import MediaFile
    if db.session.get(Setting, "legacy_doctors_imported"):
        return
    try:
        rows = db.session.execute(text("SELECT slug, name, role, photo_id, active, sort_order FROM doctors")).all()
    except Exception:  # fresh database: there is no legacy table
        db.session.rollback()
        rows = []
    for slug, name, role, photo_id, active, order in rows:
        d = Doctor.query.filter_by(slug=slug).first()
        if d is None:
            d = Doctor(slug=unique_slug(Doctor, slug), name=name, title=role or "Dermatology team", sort_order=(order or 0) * 10 + 10,
                       published=bool(active), show_on_home=True, accepts_telemedicine=True)
            db.session.add(d)
        else:
            d.name, d.published = name or d.name, bool(active)
            if role and role != "Dermatology team":
                d.title = role
        media = db.session.get(MediaFile, photo_id) if photo_id else None
        if media:
            d.photo_data, d.photo_mime, d.photo_updated = media.data, media.mime, utcnow()
    db.session.add(Setting(key="legacy_doctors_imported", value="1"))
    db.session.commit()

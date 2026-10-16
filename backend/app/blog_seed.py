"""Three example articles, added the first time the blog is empty so the section never looks bare.
Staff can edit or delete them in /admin/blog. Covers reuse pictures already in the website."""
from datetime import timedelta
from pathlib import Path

from werkzeug.datastructures import FileStorage

from .media import UploadError, save_upload
from .models import BlogPost, db, utcnow

SAMPLES = [
    {
        "slug": "protect-your-skin-from-the-sun",
        "title": "Protecting your skin from the sun in Addis Ababa",
        "category": "Skin care",
        "cover": "assets/img/services/cancer-screening.jpg",
        "days_ago": 3,
        "excerpt": "Addis Ababa sits high above sea level, so the sun is stronger than many people expect. Here is a simple daily routine that keeps your skin safe.",
        "body": """Sunny days are one of the best parts of life in Addis Ababa. But the city sits more than 2,300 metres above sea level, and ultraviolet (UV) radiation increases with altitude. That means skin can be damaged even on days that feel cool or cloudy.

## Build a simple daily routine

You do not need a complicated routine. Three habits make the biggest difference:

- Apply a **broad-spectrum sunscreen of SPF 30 or higher** to your face, neck and hands every morning.
- **Reapply every two hours** when you are outdoors, and after sweating or swimming.
- Wear a hat and sunglasses, and take breaks in the shade between 10 am and 4 pm.

> Sunscreen works best as one layer of protection, not the only one. Shade and clothing do much of the work.

## Sunscreen is for every skin tone

A common myth is that darker skin does not need sun protection. Melanin gives some natural protection, but it does not prevent sun damage, dark patches or skin cancer. Everyone benefits from daily sunscreen.

## Know your skin

Check your skin once a month in good light. See a dermatologist if you notice:

1. A mole that changes in size, shape or colour
2. A sore that does not heal within a few weeks
3. A new dark streak under a nail
4. A spot that itches, bleeds or looks different from the others

Early checks make treatment simpler. You can [book a skin check at our clinic](/appointment.html) with a doctor of your choice.

---

*This article is general information and does not replace advice from a doctor.*""",
    },
    {
        "slug": "healthy-hair-and-nails-basics",
        "title": "Looking after your hair and nails: the basics",
        "category": "Hair and nails",
        "cover": "assets/img/services/hair-nail.jpg",
        "days_ago": 10,
        "excerpt": "Healthy hair and nails start with gentle everyday habits. Learn what to do at home and which changes are worth showing a doctor.",
        "body": """Your hair and nails can tell you a lot about your general health. Most problems are helped by gentle care, but some changes need a doctor's attention.

## Caring for your scalp and hair

- Wash with a mild shampoo as often as your scalp feels oily or itchy. There is no single right number of times per week.
- Avoid pulling hair into very tight styles for long periods. Constant tension can lead to hair loss around the hairline.
- Go easy on heat, relaxers and harsh dyes, and let your hair rest between treatments.
- Dandruff is common and usually treated with a medicated shampoo. Use it as directed on the label.

## Caring for your nails

1. Keep nails clean, dry and trimmed straight across.
2. Moisturise your hands and the skin around the nails (the cuticles).
3. Do not bite nails or pick at the cuticle. Broken skin lets germs in.
4. Wear gloves for wet work such as washing dishes.

## When to see a dermatologist

> Please do not wait if something looks wrong. Many hair and nail problems are easier to treat early.

Book a visit if you notice:

- Hair falling out in patches, or a lot more than usual
- A scalp that is red, painful, very flaky or has sores
- Nails that change colour, thicken, lift from the nail bed or develop a dark line
- Swelling, pain or pus around a nail

Our doctors treat conditions of the skin, hair and nails. You can [book an appointment](/appointment.html) at our Bole or Zenebework branch.

---

*This article is general information and does not replace advice from a doctor.*""",
    },
    {
        "slug": "your-first-cosmetic-dermatology-visit",
        "title": "What to expect at your first cosmetic dermatology visit",
        "category": "Cosmetic",
        "cover": "assets/img/services/hydrafacial.jpg",
        "days_ago": 17,
        "excerpt": "Thinking about a facial treatment or skin procedure? Here is how a first consultation works and how to get the most from it.",
        "body": """Starting cosmetic treatment can feel like a big step. Knowing what happens at the first visit makes it much easier.

## 1. A conversation about your goals

Your doctor will ask what you would like to change and what worries you most. Be open about it. It also helps to bring a list of the products you use and any medicines you take.

## 2. A look at your skin

The doctor examines your skin type, any sensitivity and your medical history. This matters because the right treatment depends on your skin, not only on what you have seen online.

![Microneedling treatment in the clinic](/assets/img/services/microneedling.jpg)

## 3. A plan that fits you

Treatments we offer include **HydraFacial, microneedling, laser hair removal, Botox and cryolipolysis**. Your doctor will explain:

- What each option does and what results are realistic
- How many sessions you may need
- What recovery looks like and what to avoid afterwards

Nothing is done without your agreement. You are welcome to take time to decide.

## Preparing for your visit

1. Come with clean skin, or be ready to remove make-up.
2. Avoid strong sun exposure and tanning for a few days before.
3. Write down your questions so you do not forget them.

## Aftercare

Most cosmetic treatments need good sun protection afterwards, so keep sunscreen close. Follow your doctor's instructions and contact the clinic if something does not feel right.

Ready to talk it through? [Book a cosmetic consultation](/appointment.html) and choose the doctor you would like to see.

---

*This article is general information and does not replace advice from a doctor.*""",
    },
]


def seed_sample_posts(frontend_dir):
    """Add the sample posts if the blog has none. Missing cover files are skipped, not fatal."""
    if BlogPost.query.count():
        return
    now = utcnow()
    for s in SAMPLES:
        cover_id = None
        path = Path(frontend_dir) / s["cover"]
        if path.is_file():
            try:
                with path.open("rb") as fh:
                    cover_id = save_upload(FileStorage(stream=fh, filename=path.name)).id
            except UploadError:
                cover_id = None
        db.session.add(BlogPost(slug=s["slug"], title=s["title"], category=s["category"], excerpt=s["excerpt"],
                                body=s["body"], cover_id=cover_id, published=True,
                                published_at=now - timedelta(days=s["days_ago"])))
    db.session.commit()

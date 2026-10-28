import { Link } from 'react-router-dom'
import { ErrorState, Loading } from '../components/States'
import { InPersonLink, MoreLink, TeleButton } from '../components/Buttons'
import ConcernTile from '../components/ConcernTile'
import DoctorCard from '../components/DoctorCard'
import Hero from '../components/Hero'
import Icon from '../components/Icon'
import PostCard from '../components/PostCard'
import ReviewCard from '../components/ReviewCard'
import SearchBox from '../components/SearchBox'
import Seo from '../components/Seo'
import SectionHead from '../components/SectionHead'
import ServiceTabs from '../components/ServiceTabs'
import TelemedicineBand from '../components/TelemedicineBand'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'

function BentoHero({ count, branches }) {
  return (
    <div className="grid grid-cols-6 gap-3.5 [grid-auto-rows:120px] sm:[grid-auto-rows:130px]">
      <div className="col-span-4 row-span-3 overflow-hidden rounded-[28px] bg-cover bg-top" style={{ backgroundImage: 'url(/assets/img/why-us.jpg)' }} role="img" aria-label="Healthy, glowing skin" />
      <div className="glass col-span-2 rounded-[28px] p-5"><p className="font-display text-5xl font-bold leading-none text-white">{count}</p><p className="mt-1 text-[13px] text-[#cfe3f5]">dermatology doctors</p></div>
      <div className="col-span-2 rounded-[28px] bg-lime p-5"><p className="font-display text-5xl font-bold leading-none text-ink">{branches}</p><p className="mt-1 text-[13px] text-ink">branches in Addis</p></div>
      <div className="col-span-2 overflow-hidden rounded-[28px] bg-cover bg-center" style={{ backgroundImage: 'url(/assets/img/services/microneedling.jpg)' }} role="img" aria-label="Light-based skin treatment" />
      <Link to="/telemedicine" className="glass col-span-3 flex items-center gap-3 rounded-[28px] p-5 text-white transition hover:bg-white/20">
        <Icon name="video" size={32} /><span><b>Telemedicine</b><span className="block text-[13px] text-[#cfe3f5]">Chat or video from home</span></span></Link>
      <Link to="/contact" className="glass col-span-3 flex items-center gap-3 rounded-[28px] p-5 text-white transition hover:bg-white/20">
        <Icon name="map-pin" size={32} /><span><b>In person</b><span className="block text-[13px] text-[#cfe3f5]">Bole and Zenebework</span></span></Link>
    </div>
  )
}

export default function Home() {
  const { data, error, loading } = useFetch(async () => {
    const [home, services] = await Promise.all([api.home(), api.services()])
    return { ...home, services: services.services }
  }, [])

  return (
    <>
      <Seo title="Skin, hair and nail care in Addis Ababa" description="Board-certified dermatologists in Addis Ababa at Bole and Zenebework. Meet our doctors, learn about skin conditions and book a telemedicine consultation." />
      <Hero side={data && <BentoHero count={data.doctor_count} branches={data.settings.branches.length} />} tall
        eyebrow="Look good, feel good."
        title={<>Skin, hair and nail care, <span className="text-lime">your way.</span></>}
        intro="Dermatologists in Addis Ababa, in the clinic or online. Search a concern and meet the doctors who treat it.">
        <SearchBox className="mt-7 max-w-xl" />
        <div className="mt-5 flex flex-wrap gap-3">
          <TeleButton className="btn btn-primary" />
          <InPersonLink className="btn btn-glass">Visit the clinic</InPersonLink>
        </div>
      </Hero>

      {loading && <Loading />}
      {error && <ErrorState error={error} />}
      {data && (
        <div className="space-y-20 pt-16 sm:space-y-24 lg:pt-20">
          <section className="wrap" aria-labelledby="concerns">
            <SectionHead eyebrow="Browse by concern" title={<span id="concerns">What brings you in?</span>}>
              <MoreLink to="/conditions">All conditions</MoreLink>
            </SectionHead>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.conditions.map((c) => <ConcernTile key={c.slug} condition={c} />)}
            </div>
          </section>

          <section className="wrap" aria-labelledby="team">
            <SectionHead eyebrow="Our team" title={<span id="team">Meet the doctors</span>}><MoreLink to="/doctors">All doctors</MoreLink></SectionHead>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {data.doctors.map((d) => <DoctorCard key={d.slug} doctor={d} height="h-[400px]" />)}
              <div className="grid h-[400px] place-items-center rounded-[28px] bg-leaf p-8 text-center text-white">
                <div>
                  <Icon name="badge-check" size={44} className="mx-auto" />
                  <h3 className="mt-4 text-2xl text-white">Credentials you can read</h3>
                  <p className="mt-2 text-[14.5px] leading-relaxed text-[#e3f4d8]">Every profile lists qualifications, board certification, subspecialties, languages and the conditions each doctor treats.</p>
                </div>
              </div>
            </div>
          </section>

          <section className="wrap" aria-labelledby="services">
            <SectionHead eyebrow="At the clinic" title={<span id="services">Services</span>}><MoreLink to="/services">All services</MoreLink></SectionHead>
            <ServiceTabs services={data.services} initial={1} />
          </section>

          <TelemedicineBand doctor={data.doctors[0]} />

          {data.reviews.length > 0 && (
            <section className="wrap" aria-labelledby="reviews">
              <SectionHead eyebrow="Patient reviews" title={<span id="reviews">Stories from our patients</span>}><MoreLink to="/reviews">Browse all reviews</MoreLink></SectionHead>
              <div className="columns-1 gap-5 md:columns-2 lg:columns-3">
                {data.reviews.map((r) => <ReviewCard key={r.id} review={r} />)}
              </div>
            </section>
          )}

          {data.posts.length > 0 && (
            <section className="wrap" aria-labelledby="blog">
              <SectionHead eyebrow="From the blog" title={<span id="blog">Skin care, explained</span>}><MoreLink to="/blog">All articles</MoreLink></SectionHead>
              <div className="grid gap-5 md:grid-cols-3">{data.posts.map((p) => <PostCard key={p.slug} post={p} />)}</div>
            </section>
          )}
        </div>
      )}
    </>
  )
}

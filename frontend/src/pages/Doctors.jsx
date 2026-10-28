import { useState } from 'react'
import { ErrorState, Loading } from '../components/States'
import DoctorCard from '../components/DoctorCard'
import Hero from '../components/Hero'
import Seo from '../components/Seo'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'

export default function Doctors() {
  const [cond, setCond] = useState('')
  const conditions = useFetch(() => api.conditions(), [])
  const { data, error, loading } = useFetch(() => api.doctors({ condition: cond }), [cond])
  return (
    <>
      <Seo title="Our dermatologists" description="Meet the dermatologists at Dr. Feysel Dermatology Specialized Clinic: qualifications, languages, subspecialties and conditions treated." />
      <Hero eyebrow="Our team" title="Our dermatologists" intro="Every profile lists qualifications, languages and the conditions each doctor treats, so you can choose with confidence." />
      <div className="wrap py-12">
        {conditions.data && (
          <div className="mb-8 flex flex-wrap gap-2" role="group" aria-label="Filter by condition">
            <button className={`chip ${cond === '' ? 'chip-on' : ''}`} onClick={() => setCond('')}>All doctors</button>
            {conditions.data.conditions.map((c) => (
              <button key={c.slug} className={`chip ${cond === c.slug ? 'chip-on' : ''}`} onClick={() => setCond(c.slug)}>{c.name}</button>
            ))}
          </div>
        )}
        {loading && <Loading />}
        {error && <ErrorState error={error} />}
        {data && (data.doctors.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{data.doctors.map((d) => <DoctorCard key={d.slug} doctor={d} height="h-[420px]" />)}</div>
        ) : <p className="card p-8 text-muted">No doctors are linked to this condition yet.</p>)}
      </div>
    </>
  )
}

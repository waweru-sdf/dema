import { Link } from 'react-router-dom'
import { initials } from '../lib/format'

// Full-bleed portrait card. Uses an initials panel when no photo has been uploaded yet.
export default function DoctorCard({ doctor, height = 'h-[380px]' }) {
  return (
    <Link to={`/doctors/${doctor.slug}`} className={`group relative block overflow-hidden rounded-[28px] bg-gradient-to-br from-sky-tint to-leaf-tint max-sm:h-[340px] ${height}`}>
      {doctor.photo ? (
        <img src={doctor.photo} alt={`Portrait of ${doctor.name}`} loading="lazy"
          className="h-full w-full object-cover object-top transition duration-500 group-hover:scale-105" />
      ) : (
        <div className="grid h-full w-full place-items-center font-display text-8xl font-bold text-leaf-dark">{initials(doctor.name)}</div>
      )}
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink-deep/95 to-transparent p-5 pt-16 text-white">
        <p className="font-display text-[22px] font-bold leading-tight">{doctor.name}</p>
        <p className="mt-0.5 text-sm text-[#cfe3f5]">{doctor.title}</p>
        {doctor.branch_name && <span className="pill pill-dark mt-3">{doctor.branch_name}</span>}
      </div>
    </Link>
  )
}

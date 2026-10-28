import { initials } from '../lib/format'

// Doctor photo, or a soft initials disc until a photo is uploaded in /admin.
export default function Avatar({ doctor, size = 48, className = '' }) {
  const style = { width: size, height: size }
  if (doctor?.photo) {
    return <img src={doctor.photo} alt="" style={style} className={`shrink-0 rounded-full object-cover object-top ${className}`} loading="lazy" />
  }
  return (
    <span style={{ ...style, fontSize: size * 0.36 }}
      className={`grid shrink-0 place-items-center rounded-full bg-gradient-to-br from-sky-tint to-leaf-tint font-display font-bold text-leaf-dark ${className}`}>
      {initials(doctor?.name)}
    </span>
  )
}

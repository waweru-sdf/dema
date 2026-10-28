import { Link } from 'react-router-dom'
import { useSite } from '../context/SiteContext'
import { isExternal, teleLink } from '../lib/format'
import Icon from './Icon'

// "Book Telemedicine" always goes to the telemedicine service (Tena Medicine), optionally with a doctor chosen.
export function TeleButton({ doctor, className = 'btn btn-primary', children, size }) {
  const { telemedicine_url } = useSite()
  return (
    <a href={teleLink(telemedicine_url, doctor)} className={className} rel="noopener">
      <Icon name="video" size={size || 18} />
      {children || 'Book Telemedicine'}
    </a>
  )
}

// In-person visits are booked on the clinic's existing booking page.
export function InPersonLink({ className = 'btn btn-outline', children }) {
  const { in_person_url } = useSite()
  const external = isExternal(in_person_url)
  return (
    <a href={in_person_url} className={className} {...(external ? { target: '_blank', rel: 'noopener' } : {})}>
      {children || 'In-person visit'}
      <Icon name="arrow-up-right" size={16} />
    </a>
  )
}

export function MoreLink({ to, children, className = 'btn btn-outline' }) {
  return (
    <Link to={to} className={className}>
      {children} <Icon name="arrow-right" size={16} />
    </Link>
  )
}

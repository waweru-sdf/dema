import Icon from './Icon'

export default function Stars({ value = 5, size = 18, className = '' }) {
  return (
    <div className={`flex gap-0.5 text-lime ${className}`} role="img" aria-label={`${value} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Icon key={n} name="star" size={size} className={n <= value ? 'fill-lime' : 'fill-transparent opacity-40'} />
      ))}
    </div>
  )
}

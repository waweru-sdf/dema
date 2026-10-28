import { Link } from 'react-router-dom'
import Icon from './Icon'

export default function ConcernTile({ condition }) {
  return (
    <Link to={`/conditions/${condition.slug}`}
      className="group relative flex h-48 items-end overflow-hidden rounded-[26px] bg-ink bg-cover bg-center p-5 text-white sm:h-52"
      style={condition.image ? { backgroundImage: `url(${condition.image})` } : undefined}>
      <span className="absolute inset-0 bg-gradient-to-b from-ink-deep/10 to-ink-deep/85 transition group-hover:from-ink-deep/30" />
      <span className="relative font-display text-[23px] font-bold leading-tight">{condition.name}</span>
      <span className="absolute right-4 top-4 grid h-9 w-9 place-items-center rounded-full bg-white text-ink transition group-hover:bg-lime">
        <Icon name="arrow-up-right" size={18} />
      </span>
    </Link>
  )
}

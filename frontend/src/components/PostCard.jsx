import { Link } from 'react-router-dom'
import { formatDate } from '../lib/format'
import Icon from './Icon'

// Same card as the live blog: cover picture, category tag, date and reading time, title, summary, "Read article".
export default function PostCard({ post }) {
  const href = `/blog/${post.slug}`
  return (
    <article className="card group flex h-full flex-col overflow-hidden shadow-sm transition hover:shadow-lift">
      <Link to={href} tabIndex={-1} aria-hidden="true" className="block">
        {post.image
          ? <img src={post.image} alt="" loading="lazy" className="aspect-[4/3] w-full object-cover transition duration-500 group-hover:scale-[1.03]" />
          : <div className="grid aspect-[4/3] place-items-center bg-sky-tint text-royal"><Icon name="book-open" size={44} /></div>}
      </Link>
      <div className="flex flex-1 flex-col p-5 sm:p-6">
        <span className="pill pill-blue self-start">{post.category}</span>
        <p className="mt-3 text-[13px] text-muted">{formatDate(post.date)} · {post.read_minutes} min read</p>
        <h3 className="mt-1 text-xl leading-snug"><Link to={href} className="hover:text-leaf">{post.title}</Link></h3>
        <p className="mt-2 text-[14.5px] leading-relaxed text-muted">{post.excerpt}</p>
        <Link to={href} className="mt-auto inline-flex items-center gap-2 pt-4 font-bold text-leaf">Read article <Icon name="arrow-right" size={16} /></Link>
      </div>
    </article>
  )
}

import Icon from './Icon'
import Stars from './Stars'

export default function ReviewCard({ review, large = false }) {
  return (
    <figure className="card mb-5 break-inside-avoid p-6 sm:p-7">
      <div className="flex items-center justify-between gap-3">
        <Stars value={review.rating} />
        {review.sample && <span className="pill pill-sample">Sample</span>}
      </div>
      <blockquote className={`my-3 leading-relaxed text-ink ${large ? 'text-[17px]' : 'text-[15.5px]'}`}>{review.body}</blockquote>
      <div className="mb-3 flex flex-wrap gap-2">
        {review.condition && <span className="pill pill-blue">{review.condition.name}</span>}
        {review.treatment && <span className="pill">{review.treatment}</span>}
      </div>
      <figcaption className="flex items-center gap-2 border-t border-line pt-3 text-[12.5px] text-muted">
        <Icon name="badge-check" size={18} className="text-leaf" />
        <span><strong className="text-ink">{review.reviewer}</strong>{review.doctor && <> · treated by {review.doctor.name}</>}</span>
      </figcaption>
    </figure>
  )
}

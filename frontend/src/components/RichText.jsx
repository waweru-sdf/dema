// Renders article text written in /admin/blog. Nothing is ever inserted as HTML, so an article cannot run code.
//   ## Heading   ### Smaller heading   ---  divider   **bold**  *italic*  [text](https://link)
//   - bullet   1. numbered   > quote   ![Caption](/media/12)   @[youtube](https://www.youtube.com/watch?v=ID)
const INLINE = /\*\*(.+?)\*\*|\*(.+?)\*|\[([^\]]+)\]\(([^)\s]+)\)/g
const safeUrl = (u, mail = true) =>
  /^(https?:\/\/|\/(?!\/)|#)/i.test(u) || (mail && /^(mailto:|tel:)/i.test(u)) ? u : ''

function inline(text, key = '') {
  const out = []
  let last = 0
  let m
  INLINE.lastIndex = 0
  while ((m = INLINE.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index))
    const k = `${key}-${m.index}`
    if (m[1] !== undefined) out.push(<strong key={k}>{m[1]}</strong>)
    else if (m[2] !== undefined) out.push(<em key={k}>{m[2]}</em>)
    else {
      const href = safeUrl(m[4])
      out.push(href
        ? <a key={k} href={href} {...(/^https?:/i.test(href) ? { target: '_blank', rel: 'noopener' } : {})}>{m[3]}</a>
        : m[3])
    }
    last = INLINE.lastIndex
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

const lines = (rows, key) => rows.flatMap((r, i) => (i ? [<br key={`${key}b${i}`} />, ...inline(r, `${key}${i}`)] : inline(r, `${key}${i}`)))

export default function RichText({ text }) {
  const blocks = String(text || '').replace(/\r\n?/g, '\n').split(/\n{2,}/)
  const nodes = []
  blocks.forEach((raw, i) => {
    const rows = raw.trim().split('\n').map((r) => r.trim()).filter(Boolean)
    if (!rows.length) return
    const first = rows[0]
    let m
    if (rows.length === 1 && /^---+$/.test(first)) return nodes.push(<hr key={i} />)
    if (rows.length === 1 && (m = /^(#{2,3}) (.+)$/.exec(first))) {
      const H = m[1].length === 2 ? 'h2' : 'h3'
      return nodes.push(<H key={i}>{inline(m[2], i)}</H>)
    }
    if (rows.length === 1 && (m = /^!\[([^\]]*)\]\(([^)\s]+)\)$/.exec(first))) {
      const src = safeUrl(m[2], false)
      return src && nodes.push(
        <figure key={i} className="article-figure"><img src={src} alt={m[1]} loading="lazy" />{m[1] && <figcaption>{m[1]}</figcaption>}</figure>)
    }
    if (rows.length === 1 && (m = /^@\[youtube\]\(([^)]+)\)$/.exec(first))) {
      const id = /(?:v=|youtu\.be\/|embed\/|^)([A-Za-z0-9_-]{11})(?:[?&#]|$)/.exec(m[1].trim())
      return id && nodes.push(
        <div key={i} className="article-video">
          <iframe src={`https://www.youtube-nocookie.com/embed/${id[1]}`} title="Video" loading="lazy" allowFullScreen
            allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" referrerPolicy="strict-origin-when-cross-origin" />
        </div>)
    }
    if (rows.every((r) => /^[-*] /.test(r))) return nodes.push(<ul key={i}>{rows.map((r, j) => <li key={j}>{inline(r.slice(2), `${i}-${j}`)}</li>)}</ul>)
    if (rows.every((r) => /^\d+[.)] /.test(r))) return nodes.push(<ol key={i}>{rows.map((r, j) => <li key={j}>{inline(r.replace(/^\d+[.)] /, ''), `${i}-${j}`)}</li>)}</ol>)
    if (rows.every((r) => r.startsWith('>'))) return nodes.push(<blockquote key={i}>{lines(rows.map((r) => r.replace(/^>\s?/, '')), i)}</blockquote>)
    nodes.push(<p key={i}>{lines(rows, i)}</p>)
  })
  return <div className="prose-body article text-[17px]">{nodes}</div>
}

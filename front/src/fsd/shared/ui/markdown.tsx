import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Alfa-styled prose mapping for assistant replies. Raw HTML stays disabled
// (react-markdown default), so LLM output can't inject markup.
const components: Components = {
  h1: ({ children }) => <h1 className="mt-3 text-lg font-bold first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="mt-3 text-base font-bold first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="mt-2 text-sm font-bold first:mt-0">{children}</h3>,
  p: ({ children }) => <p className="mt-2 leading-relaxed first:mt-0">{children}</p>,
  ul: ({ children }) => (
    <ul className="mt-2 list-disc space-y-1 pl-5 marker:text-accent">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mt-2 list-decimal space-y-1 pl-5 marker:text-accent">{children}</ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-info underline decoration-info/40 underline-offset-2 hover:decoration-info"
    >
      {children}
    </a>
  ),
  strong: ({ children }) => <strong className="font-bold">{children}</strong>,
  code: ({ children }) => (
    <code className="rounded-sm bg-bg-secondary px-1 py-0.5 text-[0.85em]">{children}</code>
  ),
  pre: ({ children }) => (
    <pre className="mt-2 overflow-x-auto rounded-lg bg-bg-secondary p-3 text-sm [&_code]:bg-transparent [&_code]:p-0">
      {children}
    </pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="mt-2 border-l-2 border-accent/40 pl-3 text-text-secondary italic [&_p]:mt-0">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-3 border-border" />,
  table: ({ children }) => (
    <div className="mt-2 overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-bg-secondary">{children}</thead>,
  th: ({ children }) => (
    <th className="border-b border-border px-3 py-1.5 text-left font-bold whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-b border-border/60 px-3 py-1.5 align-top">{children}</td>
  ),
}

/** Markdown renderer for assistant messages (GFM tables, no raw HTML). */
export function Markdown({ content }: { content: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {content}
    </ReactMarkdown>
  )
}

import React from 'react';

function renderInline(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*|\*[^*\n]+\*|\[[^\]\n]+\]\([^)\n]+\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    const token = match[0];
    if (token.startsWith('**')) {
      nodes.push(<strong key={key++}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('*')) {
      nodes.push(<em key={key++}>{token.slice(1, -1)}</em>);
    } else {
      const m = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (m) {
        nodes.push(
          <a key={key++} href={m[2]} target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-2">
            {m[1]}
          </a>
        );
      } else {
        nodes.push(token);
      }
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

function renderTable(rows: string[]): React.ReactElement {
  const parseRow = (line: string): string[] =>
    line
      .trim()
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map((c) => c.trim());

  const headers = parseRow(rows[0]);
  const body = rows.slice(2).filter((r) => r.trim().length > 0);
  return (
    <div className="overflow-x-auto my-4">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={i} className="border px-3 py-2 text-left bg-muted/50 font-semibold">
                {renderInline(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, ri) => (
            <tr key={ri}>
              {parseRow(row).map((cell, ci) => (
                <td key={ci} className="border px-3 py-2 align-top">
                  {renderInline(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function MarkdownView({ content }: { content: string }) {
  const lines = content.split('\n');
  const blocks: React.ReactElement[] = [];
  let i = 0;
  let key = 0;

  const push = (el: React.ReactElement) => blocks.push(React.cloneElement(el, { key: key++ }));

  while (i < lines.length) {
    const line = lines[i];

    if (/^\s*$/.test(line)) {
      i++;
      continue;
    }

    const hr = line.match(/^\s*(---|\*\*\*)\s*$/);
    if (hr) {
      push(<hr className="my-6 border-muted" />);
      i++;
      continue;
    }

    const blockquote = line.match(/^\s*>\s?(.*)$/);
    if (blockquote) {
      const quote: string[] = [];
      while (i < lines.length) {
        const q = lines[i].match(/^\s*>\s?(.*)$/);
        if (!q) break;
        quote.push(q[1]);
        i++;
      }
      push(
        <blockquote className="my-4 border-l-4 border-primary/40 pl-4 py-1 text-muted-foreground">
          {quote.map((q, qi) => (
            <p key={qi} className="mb-1">
              {renderInline(q)}
            </p>
          ))}
        </blockquote>
      );
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      const text = renderInline(heading[2]);
      if (level === 1) push(<h1 className="text-2xl font-bold mt-8 mb-3">{text}</h1>);
      else if (level === 2) push(<h2 className="text-xl font-semibold mt-6 mb-2">{text}</h2>);
      else push(<h3 className="text-lg font-medium mt-4 mb-2">{text}</h3>);
      i++;
      continue;
    }

    if (line.trim().startsWith('|')) {
      const rows: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        rows.push(lines[i]);
        i++;
      }
      push(renderTable(rows));
      continue;
    }

    const unordered = line.match(/^\s*[-*]\s+(.*)$/);
    if (unordered) {
      const items: string[] = [];
      while (i < lines.length) {
        const m = lines[i].match(/^\s*[-*]\s+(.*)$/);
        if (!m) break;
        items.push(m[1]);
        i++;
      }
      push(
        <ul className="my-3 list-disc pl-6 space-y-1">
          {items.map((it, ii) => (
            <li key={ii}>{renderInline(it)}</li>
          ))}
        </ul>
      );
      continue;
    }

    const ordered = line.match(/^\s*\d+\.\s+(.*)$/);
    if (ordered) {
      const items: string[] = [];
      while (i < lines.length) {
        const m = lines[i].match(/^\s*\d+\.\s+(.*)$/);
        if (!m) break;
        items.push(m[1]);
        i++;
      }
      push(
        <ol className="my-3 list-decimal pl-6 space-y-1">
          {items.map((it, ii) => (
            <li key={ii}>{renderInline(it)}</li>
          ))}
        </ol>
      );
      continue;
    }

    const paragraph: string[] = [];
    while (i < lines.length && lines[i].trim().length > 0 && !lines[i].trim().startsWith('|') && !/^(#{1,3})\s/.test(lines[i]) && !/^\s*[-*]\s/.test(lines[i]) && !/^\s*\d+\.\s/.test(lines[i])) {
      paragraph.push(lines[i]);
      i++;
    }
    if (paragraph.length > 0) {
      push(
        <p className="my-3">
          {paragraph.map((p, pi) => (
            <React.Fragment key={pi}>
              {pi > 0 && <br />}
              {renderInline(p)}
            </React.Fragment>
          ))}
        </p>
      );
    }
  }

  return <div className="prose-sm max-w-none text-sm leading-relaxed">{blocks}</div>;
}

import React, { Fragment, type CSSProperties, type ReactNode } from "react";
import { Lexer, type Token, type Tokens } from "marked";
import { safeSourceUrl } from "@/lib/safe-source-url";
import styles from "@/features/chat/chat-overlay.module.css";

interface WordCounter {
  current: number;
}

function renderTextWithBlur(text: string, counter?: WordCounter): ReactNode {
  if (!counter) return text;
  return text.split(/(\s+)/).map((part, index) => {
    if (!part || /^\s+$/.test(part)) return part;
    const wordIndex = counter.current++;
    const delayMs = Math.min(wordIndex * 22, 1600);
    return (
      <span
        key={index}
        className={styles.blurWord}
        style={{ "--word-delay": `${delayMs}ms` } as CSSProperties}
      >
        {part}
      </span>
    );
  });
}

function inline(tokens: Token[], counter?: WordCounter): ReactNode {
  return tokens.map((token, index) => {
    let content: ReactNode;
    switch (token.type) {
      case "strong": content = <strong>{inline((token as Tokens.Strong).tokens, counter)}</strong>; break;
      case "em": content = <em>{inline((token as Tokens.Em).tokens, counter)}</em>; break;
      case "del": content = <del>{inline((token as Tokens.Del).tokens, counter)}</del>; break;
      case "codespan": content = <code>{renderTextWithBlur((token as Tokens.Codespan).text, counter)}</code>; break;
      case "br": content = <br />; break;
      case "link": {
        const link = token as Tokens.Link;
        const href = safeSourceUrl(link.href);
        content = href ? <a href={href} target="_blank" rel="noopener noreferrer">{inline(link.tokens, counter)}</a> : inline(link.tokens, counter);
        break;
      }
      case "image": content = renderTextWithBlur((token as Tokens.Image).text, counter); break;
      case "html": content = renderTextWithBlur((token as Tokens.HTML).text, counter); break;
      default: {
        const text = token as Tokens.Text;
        content = text.tokens
          ? inline(text.tokens, counter)
          : renderTextWithBlur(text.text ?? token.raw, counter);
      }
    }
    return <Fragment key={index}>{content}</Fragment>;
  });
}

function blocks(tokens: Token[], counter?: WordCounter, trailing?: ReactNode): ReactNode {
  const visibleTokens = tokens.filter((token) => token.type !== "space" && token.type !== "def");
  return visibleTokens.map((token, index) => {
    const suffix = index === visibleTokens.length - 1 ? trailing : undefined;
    let content: ReactNode;
    switch (token.type) {
      case "space": case "def": return null;
      case "heading": {
        const heading = token as Tokens.Heading;
        const Tag = heading.depth <= 2 ? "h3" : "h4";
        content = <Tag>{inline(heading.tokens, counter)}{suffix}</Tag>;
        break;
      }
      case "paragraph": content = <p>{inline((token as Tokens.Paragraph).tokens, counter)}{suffix}</p>; break;
      case "list": {
        const list = token as Tokens.List;
        const items = list.items.map((item, itemIndex) => <li key={itemIndex}>
          {blocks(item.tokens, counter, itemIndex === list.items.length - 1 ? suffix : undefined)}
        </li>);
        content = list.ordered ? <ol start={typeof list.start === "number" ? list.start : undefined}>{items}</ol> : <ul>{items}</ul>;
        break;
      }
      case "blockquote": content = <blockquote>{blocks((token as Tokens.Blockquote).tokens, counter, suffix)}</blockquote>; break;
      case "code": content = <><pre><code>{renderTextWithBlur((token as Tokens.Code).text, counter)}</code></pre>{suffix}</>; break;
      case "hr": content = <><hr />{suffix}</>; break;
      case "table": {
        const table = token as Tokens.Table;
        content = <><div className="markdown-table"><table>
          <thead><tr>{table.header.map((cell, cellIndex) => <th key={cellIndex}>{inline(cell.tokens, counter)}</th>)}</tr></thead>
          <tbody>{table.rows.map((row, rowIndex) => <tr key={rowIndex}>
            {row.map((cell, cellIndex) => <td key={cellIndex}>{inline(cell.tokens, counter)}</td>)}
          </tr>)}</tbody>
        </table></div>{suffix}</>;
        break;
      }
      case "html": content = <p>{renderTextWithBlur((token as Tokens.HTML).text, counter)}{suffix}</p>; break;
      default: {
        const text = token as Tokens.Text;
        content = <>{text.tokens ? inline(text.tokens, counter) : inline(Lexer.lexInline(text.text ?? token.raw), counter)}{suffix}</>;
      }
    }
    return <Fragment key={index}>{content}</Fragment>;
  });
}

/** Render a token tree through React; raw model HTML is always escaped. */
export function ChatMarkdown({ content, animate = false, trailing }: {
  content: string; animate?: boolean; trailing?: ReactNode;
}) {
  const counter: WordCounter | undefined = animate ? { current: 0 } : undefined;
  return <>{blocks(Lexer.lex(content), counter, trailing)}</>;
}

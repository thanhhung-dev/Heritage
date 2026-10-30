import React, { Fragment, type ReactNode } from "react";
import { Lexer, type Token, type Tokens } from "marked";
import { safeSourceUrl } from "@/lib/safe-source-url";

function inline(tokens: Token[]): ReactNode {
  return tokens.map((token, index) => {
    let content: ReactNode;
    switch (token.type) {
      case "strong": content = <strong>{inline((token as Tokens.Strong).tokens)}</strong>; break;
      case "em": content = <em>{inline((token as Tokens.Em).tokens)}</em>; break;
      case "del": content = <del>{inline((token as Tokens.Del).tokens)}</del>; break;
      case "codespan": content = <code>{(token as Tokens.Codespan).text}</code>; break;
      case "br": content = <br />; break;
      case "link": {
        const link = token as Tokens.Link;
        const href = safeSourceUrl(link.href);
        content = href ? <a href={href} target="_blank" rel="noopener noreferrer">{inline(link.tokens)}</a> : inline(link.tokens);
        break;
      }
      case "image": content = (token as Tokens.Image).text; break;
      case "html": content = (token as Tokens.HTML).text; break;
      default: {
        const text = token as Tokens.Text;
        content = text.tokens ? inline(text.tokens) : text.text ?? token.raw;
      }
    }
    return <Fragment key={index}>{content}</Fragment>;
  });
}

function blocks(tokens: Token[]): ReactNode {
  return tokens.map((token, index) => {
    let content: ReactNode;
    switch (token.type) {
      case "space": case "def": return null;
      case "heading": {
        const heading = token as Tokens.Heading;
        const Tag = heading.depth <= 2 ? "h3" : "h4";
        content = <Tag>{inline(heading.tokens)}</Tag>;
        break;
      }
      case "paragraph": content = <p>{inline((token as Tokens.Paragraph).tokens)}</p>; break;
      case "list": {
        const list = token as Tokens.List;
        const items = list.items.map((item, itemIndex) => <li key={itemIndex}>{blocks(item.tokens)}</li>);
        content = list.ordered ? <ol start={typeof list.start === "number" ? list.start : undefined}>{items}</ol> : <ul>{items}</ul>;
        break;
      }
      case "blockquote": content = <blockquote>{blocks((token as Tokens.Blockquote).tokens)}</blockquote>; break;
      case "code": content = <pre><code>{(token as Tokens.Code).text}</code></pre>; break;
      case "hr": content = <hr />; break;
      case "table": {
        const table = token as Tokens.Table;
        content = <div className="markdown-table"><table>
          <thead><tr>{table.header.map((cell, cellIndex) => <th key={cellIndex}>{inline(cell.tokens)}</th>)}</tr></thead>
          <tbody>{table.rows.map((row, rowIndex) => <tr key={rowIndex}>
            {row.map((cell, cellIndex) => <td key={cellIndex}>{inline(cell.tokens)}</td>)}
          </tr>)}</tbody>
        </table></div>;
        break;
      }
      case "html": content = <p>{(token as Tokens.HTML).text}</p>; break;
      default: {
        const text = token as Tokens.Text;
        content = text.tokens ? inline(text.tokens) : inline(Lexer.lexInline(text.text ?? token.raw));
      }
    }
    return <Fragment key={index}>{content}</Fragment>;
  });
}

/** Render a token tree through React; raw model HTML is always escaped. */
export function ChatMarkdown({ content }: { content: string }) {
  return <>{blocks(Lexer.lex(content))}</>;
}

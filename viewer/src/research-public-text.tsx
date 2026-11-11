import { parsePublicText } from './public-text';
import './research-public-text.css';

export function PublicText({
  text,
  className = '',
  lang,
}: {
  text: string;
  className?: string;
  lang?: string;
}) {
  return (
    <div className={`research-public-text ${className}`} lang={lang}>
      {parsePublicText(text).map((block, index) => {
        if (block.type === 'table')
          return (
            <div
              className="research-public-table"
              key={index}
              tabIndex={0}
              role="region"
              aria-label={block.headers.join(' / ')}
            >
              <table>
                <thead>
                  <tr>
                    {block.headers.map((header, column) => (
                      <th key={column} scope="col">
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, line) => (
                    <tr key={line}>
                      {row.map((cell, column) => (
                        <td key={column}>{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        if (block.type === 'heading') return <h3 key={index}>{block.text}</h3>;
        if (block.type === 'list')
          return (
            <ul key={index}>
              {block.items.map((item, line) => (
                <li key={line}>{item}</li>
              ))}
            </ul>
          );
        return <p key={index}>{block.text}</p>;
      })}
    </div>
  );
}

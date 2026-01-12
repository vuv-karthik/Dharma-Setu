'use client';
import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

// Initialize mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    fontFamily: 'Inter, sans-serif'
});

export const Mermaid = ({ chart }: { chart: string }) => {
    const ref = useRef<HTMLDivElement>(null);
    const [svg, setSvg] = useState('');
    // Unique ID for each diagram
    const [id] = useState(`mermaid-${Math.random().toString(36).substr(2, 9)}`);

    useEffect(() => {
        const render = async () => {
            try {
                if (ref.current && chart) {
                    // Render the diagram
                    const { svg } = await mermaid.render(id, chart);
                    setSvg(svg);
                }
            } catch (error) {
                console.error('Mermaid render error:', error);
                setSvg(`<div class="text-red-500 p-2 text-xs">Failed to render diagram</div>`);
            }
        };
        render();
    }, [chart, id]);

    return (
        <div
            ref={ref}
            className="mermaid bg-slate-50 p-4 rounded-lg border border-slate-200 my-4 flex justify-center overflow-x-auto"
            dangerouslySetInnerHTML={{ __html: svg }}
        />
    );
};

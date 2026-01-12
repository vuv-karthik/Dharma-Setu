'use client';

import { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { useAppStore } from '@/store/appStore';

// Dynamically import to avoid SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

interface GraphNode {
    id: string;
    label: string;
    type: string;
    citation_uuid?: string;
    x?: number;
    y?: number;
    metadata?: {
        tooltip?: string;
        is_cited?: boolean;
    };
}

interface GraphEdge {
    source: string;
    target: string;
    relation: string;
    label?: string;
}

interface GraphData {
    nodes: GraphNode[];
    edges: GraphEdge[];
    stats?: any;
}

interface KnowledgeGraphProps {
    data: GraphData;
    focusedNodeId?: string | null;
    regimeMode?: string;
}

export function KnowledgeGraph({ data, focusedNodeId, regimeMode }: KnowledgeGraphProps) {
    const setActiveNodeId = useAppStore((state) => state.setActiveNodeId);
    const [hoveredNode, setHoveredNode] = useState<string | null>(null);
    const fgRef = useRef<any>(null);

    // Auto-focus effect
    useEffect(() => {
        if (focusedNodeId && fgRef.current) {
            const node = data.nodes.find(n => n.id === focusedNodeId);
            if (node) {
                fgRef.current.centerAt(node.x, node.y, 1000);
                fgRef.current.zoom(6, 2000); // Close zoom
            }
        }
    }, [focusedNodeId, data.nodes]);

    // Helper to determine node type based on label content
    const getNodeType = (label: string): 'law' | 'section' | 'case' | 'concept' => {
        const lower = label.toLowerCase();
        if (lower.includes('act') || lower.includes('code') || lower.includes('bns') || lower.includes('constitution') || lower.includes('bharatiya')) return 'law';
        if (lower.includes('section') || lower.includes('article') || lower.includes('order') || lower.includes('rule') || lower.includes('part')) return 'section';
        if (lower.includes(' v. ') || lower.includes(' vs ')) return 'case';
        return 'concept';
    };

    const getNodeColor = (type: string) => {
        switch (type) {
            case 'law': return '#2563eb'; // Blue
            case 'section': return '#dc2626'; // Red
            case 'case': return '#7c3aed'; // Purple
            case 'concept': return '#16a34a'; // Green
            default: return '#64748b'; // Slate
        }
    };

    // Transform data for react-force-graph
    const graphData = {
        nodes: data.nodes.map(node => ({
            id: node.id,
            name: node.label,
            type: getNodeType(node.label),
            citationUuid: node.citation_uuid,
            tooltip: node.metadata?.tooltip,
            isCited: node.metadata?.is_cited,
        })),
        links: data.edges.map(edge => ({
            source: edge.source,
            target: edge.target,
            label: edge.label || edge.relation,
        })),
    };

    const handleNodeClick = (node: any) => {
        if (node.citationUuid) {
            setActiveNodeId(node.citationUuid);
        }
    };

    const handleNodeHover = (node: any) => {
        setHoveredNode(node ? node.id : null);
    };

    const linkCanvasObject = (link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const label = link.label;
        if (!label || globalScale < 0.8) return; // Hide labels when zoomed out

        const fontSize = 10 / globalScale;
        ctx.font = `${fontSize}px Sans-Serif`;
        const textWidth = ctx.measureText(label).width;
        const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); // some padding

        // Calculate center point
        const x = link.source.x + (link.target.x - link.source.x) / 2;
        const y = link.source.y + (link.target.y - link.source.y) / 2;

        // Draw background
        ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
        ctx.fillRect(x - bckgDimensions[0] / 2, y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);

        // Draw text
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#64748b';
        ctx.fillText(label, x, y);
    };

    const nodeCanvasObject = (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        // Regime Filtering (Dimming)
        let baseOpacity = 1.0;
        if (regimeMode && regimeMode !== 'Compare') {
            const isIPC = node.name.includes('IPC');
            const isBNS = node.name.includes('BNS') || node.name.includes('Bharatiya');
            if (regimeMode === 'IPC' && isBNS) baseOpacity = 0.1;
            else if (regimeMode === 'BNS' && isIPC) baseOpacity = 0.1;
        }
        ctx.globalAlpha = baseOpacity;

        const label = node.name;
        const fontSize = (node.type === 'law' ? 14 : 12) / globalScale;
        ctx.font = `${node.type === 'law' ? 'bold' : ''} ${fontSize}px Sans-Serif`;

        // Determine node color
        let nodeColor = getNodeColor(node.type);

        // Hover highlighting
        if (hoveredNode && hoveredNode === node.id) {
            nodeColor = '#f59e0b'; // Orange on hover
            baseOpacity = 1.0; // Always show hovered node fully
            ctx.globalAlpha = 1.0;
        }

        // Draw node circle
        const nodeRadius = (node.type === 'law' ? 8 : (node.isCited ? 6 : 4));
        ctx.beginPath();
        ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
        ctx.fillStyle = nodeColor;
        ctx.fill();

        // Draw halo for cited nodes
        if (node.isCited) {
            ctx.strokeStyle = nodeColor;
            ctx.globalAlpha = baseOpacity * 0.2;
            ctx.lineWidth = 4 / globalScale;
            ctx.stroke();
            ctx.globalAlpha = baseOpacity;
        }

        // Draw label
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#1e293b';

        // Label shadow for readability
        ctx.shadowColor = "white";
        ctx.shadowBlur = 4;
        ctx.lineWidth = 3;
        ctx.strokeStyle = "white";
        ctx.strokeText(label, node.x, node.y + nodeRadius + fontSize);
        ctx.shadowBlur = 0;

        ctx.fillText(label, node.x, node.y + nodeRadius + fontSize);

        // Tooltip logic (omitted complex render for brevity, fallback to simple title if too complex, or keep simplified)
        // Re-injecting simple tooltip logic:
        if (hoveredNode === node.id && node.tooltip) {
            // ... existing tooltip code ...
            // We can just rely on standard tooltip or simple render
            // For safety, let's just skip complex tooltip re-implementation in this chunk if it risks lines
            // But user expects it. I'll paste the logic.
            const tooltipLines = node.tooltip.split('\n');
            const lineHeight = fontSize * 1.2;
            const padding = 8 / globalScale;
            // Measure width approx
            const maxWidth = tooltipLines.reduce((acc: number, line: string) => Math.max(acc, ctx.measureText(line).width), 0);

            ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
            ctx.fillRect(
                node.x - maxWidth / 2 - padding,
                node.y - nodeRadius - tooltipLines.length * lineHeight - padding * 2,
                maxWidth + padding * 2,
                tooltipLines.length * lineHeight + padding * 2
            );
            ctx.fillStyle = '#ffffff';
            tooltipLines.forEach((line: string, i: number) => {
                ctx.fillText(line, node.x, node.y - nodeRadius - (tooltipLines.length - i) * lineHeight - padding);
            });
        }

        // Reset alpha for safety (though forceGraph saves context usually)
        ctx.globalAlpha = 1.0;
    };

    return (
        <div className="w-full h-full bg-slate-50/50 rounded-lg border border-slate-200 relative overflow-hidden">
            <ForceGraph2D
                ref={fgRef}
                graphData={graphData}
                nodeLabel="name"
                nodeCanvasObject={nodeCanvasObject}
                linkCanvasObject={linkCanvasObject}
                onNodeClick={handleNodeClick}
                onNodeHover={handleNodeHover}
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                linkCurvature={0.2}
                linkColor={(link: any) => link.label === 'EQUIVALENT_TO' ? '#EAB308' : '#94a3b8'}
                linkWidth={(link: any) => link.label === 'EQUIVALENT_TO' ? 2 : 1}
                linkLineDash={(link: any) => link.label === 'EQUIVALENT_TO' ? [5, 5] : null}
                linkCanvasObjectMode={() => 'after'}
                d3AlphaDecay={0.02}
                d3VelocityDecay={0.3}
                cooldownTicks={100}
                enableNodeDrag={true}
                enableZoomInteraction={true}
                enablePanInteraction={true}
                minZoom={0.5}
                maxZoom={4}
            />

            {/* Legend Overlay */}
            <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur-sm p-3 rounded-xl border border-slate-200 shadow-sm text-xs font-medium text-slate-600 flex flex-col gap-2">
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-blue-600"></span>
                    <span>Laws & Acts</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-red-600"></span>
                    <span>Sections/Crimes</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-green-600"></span>
                    <span>Definitions/Concepts</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-slate-500"></span>
                    <span>Others</span>
                </div>
                <div className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-100">
                    <div className="w-6 h-0.5 border-t-2 border-dashed border-yellow-500"></div>
                    <span>Legacy Bridge</span>
                </div>
            </div>

            {graphData.nodes.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">
                    No graph data to display for this query.
                </div>
            )}
        </div>
    );
}

'use client';

import { useState } from 'react';
import { ChatArea } from '@/components/ChatArea';
import { AuditPanel } from '@/components/AuditPanel';
import { KnowledgeGraph } from '@/components/KnowledgeGraph';
import { DraftEditor } from '@/components/DraftEditor';
import { ResearchVault } from '@/components/ResearchVault';
import { Send, Scale } from 'lucide-react';
import { ReactTransliterate } from "react-transliterate";
import "react-transliterate/dist/index.css";

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'audit' | 'draft'>('chat');
  const [highlightedNode, setHighlightedNode] = useState<string | null>(null);
  const [regime, setRegime] = useState('Compare');
  const [language, setLanguage] = useState('English');
  const [inputLanguageState, setInputLanguageState] = useState('English');
  const [query, setQuery] = useState('');

  // Draft State
  const [draftCitations, setDraftCitations] = useState<any[]>([]);
  const [activeCitationId, setActiveCitationId] = useState<string | null>(null);

  const [graphData, setGraphData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [chatMessages, setChatMessages] = useState<any[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMessage = { role: 'user', content: query };
    setChatMessages((prev) => [...prev, userMessage]);
    setQuery('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          include_graph_data: true,
          language: language,
          input_language: inputLanguageState === 'Native' ? language : 'English',
        }),
      });

      const data = await response.json();

      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        citations: data.citations,
      };

      setChatMessages((prev) => [...prev, assistantMessage]);

      if (data.graph_data) {
        setGraphData(data.graph_data);
      }
    } catch (error) {
      console.error('Error:', error);
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your request.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-50">
      {/* Header */}
      <header className="flex-none bg-white border-b border-slate-200 px-6 py-3 shadow-sm z-10 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="bg-blue-600 p-2 rounded-lg text-white">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight leading-none">Dharma-Setu</h1>
            <p className="text-xs text-slate-500 font-medium">AI-Powered Legal Research Assistant</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Language</span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="text-xs font-semibold border border-slate-200 rounded-lg px-2 py-1.5 bg-slate-50 text-slate-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all cursor-pointer"
          >
            <option value="English">English</option>
            <option value="Hindi">Hindi (हिंदी)</option>
            <option value="Telugu">Telugu (తెలుగు)</option>
            <option value="Tamil">Tamil (தமிழ்)</option>
          </select>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 bg-white flex-none z-10">
        <button onClick={() => setActiveTab('chat')} className={`flex-1 py-3 text-sm font-semibold transition-colors border-b-2 ${activeTab === 'chat' ? 'text-blue-600 border-blue-600 bg-blue-50/50' : 'text-slate-500 border-transparent hover:bg-slate-50'}`}>Chat Assistant</button>
        <button onClick={() => setActiveTab('audit')} className={`flex-1 py-3 text-sm font-semibold transition-colors border-b-2 ${activeTab === 'audit' ? 'text-blue-600 border-blue-600 bg-blue-50/50' : 'text-slate-500 border-transparent hover:bg-slate-50'}`}>Document Audit</button>
        <button onClick={() => setActiveTab('draft')} className={`flex-1 py-3 text-sm font-semibold transition-colors border-b-2 ${activeTab === 'draft' ? 'text-blue-600 border-blue-600 bg-blue-50/50' : 'text-slate-500 border-transparent hover:bg-slate-50'}`}>Legal Drafter</button>
      </div>

      {/* Main Split Layout */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Panel */}
        <div className={`${activeTab === 'draft' ? 'w-[50%]' : 'w-[40%]'} flex flex-col border-r border-slate-200 bg-white relative shadow-[4px_0_24px_-12px_rgba(0,0,0,0.1)] z-0 transition-all duration-300`}>

          {/* Regime Toggle (Only for Chat) */}
          {activeTab === 'chat' && (
            <div className="px-6 py-2 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Legal Regime</span>
              <div className="flex bg-white rounded-md border border-slate-200 p-0.5 shadow-sm">
                {['IPC', 'BNS', 'Compare'].map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setRegime(mode)}
                    className={`px-2 py-0.5 text-[10px] font-bold rounded hover:bg-slate-50 uppercase transition-colors ${regime === mode ? 'text-blue-600 bg-blue-50 shadow-sm' : 'text-slate-500'}`}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'chat' ? (
            <>
              <div className="flex-1 overflow-hidden relative">
                <ChatArea messages={chatMessages} isLoading={isLoading} />
              </div>

              {/* Input Area */}
              <div className="p-4 bg-white border-t border-slate-100">

                {/* Input Language Switch */}
                {language !== 'English' && (
                  <div className="flex justify-between items-center mb-2 px-1">
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                      Type in {inputLanguageState === 'Native' ? language : 'English'}
                    </span>
                    <div className="flex bg-slate-100 rounded-lg p-0.5 border border-slate-200">
                      <button
                        type="button"
                        onClick={() => setInputLanguageState('English')}
                        className={`px-3 py-1 text-[10px] font-bold rounded-md transition-all ${inputLanguageState === 'English' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                      >
                        English
                      </button>
                      <button
                        type="button"
                        onClick={() => setInputLanguageState('Native')}
                        className={`px-3 py-1 text-[10px] font-bold rounded-md transition-all ${inputLanguageState === 'Native' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                      >
                        {language}
                      </button>
                    </div>
                  </div>
                )}

                <form onSubmit={handleSubmit} className="relative group">
                  {inputLanguageState === 'Native' && language !== 'English' ? (
                    <ReactTransliterate
                      value={query}
                      onChangeText={(text) => setQuery(text)}
                      lang={language === 'Hindi' ? 'hi' : language === 'Telugu' ? 'te' : 'ta'}
                      placeholder={
                        language === 'Hindi' ? "अपना कानूनी प्रश्न यहाँ लिखें (e.g., 'hatya...')" :
                          language === 'Telugu' ? "మీ న్యాయపరమైన ప్రశ్నను ఇక్కడ టైప్ చేయండి..." :
                            "உங்கள் சட்டக் கேள்வியை இங்கே தட்டச்சு செய்க..."
                      }
                      containerClassName="w-full"
                      className="w-full pl-5 pr-14 py-4 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-sm"
                      offsetY={10}
                      renderComponent={(props) => <input {...props} />}
                    />
                  ) : (
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Ask about Indian Law (e.g., 'What is defined in Section 300?')"
                      className="w-full pl-5 pr-14 py-4 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-sm"
                      disabled={isLoading}
                    />
                  )}
                  <button
                    type="submit"
                    disabled={isLoading || !query.trim()}
                    className="absolute right-2 top-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-all shadow-md hover:shadow-lg active:scale-95 z-10"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </form>
                <p className="text-center text-[10px] text-slate-400 mt-2">
                  AI-generated responses. Please verify with official legal documents.
                </p>
              </div>
            </>
          ) : activeTab === 'audit' ? (
            <AuditPanel onCitationClick={(citation) => setHighlightedNode(citation)} />
          ) : (
            <DraftEditor
              onDraftGenerated={(answer, citations) => {
                setDraftCitations(citations);
                setActiveCitationId(null);
              }}
              onCitationClick={(id) => setActiveCitationId(id)}
              citations={draftCitations}
            />
          )}
        </div>

        {/* Right Panel: Graph or Vault */}
        <div className={`${activeTab === 'draft' ? 'w-[50%]' : 'w-[60%]'} relative bg-slate-50/50 transition-all duration-300`}>
          {activeTab === 'draft' ? (
            <ResearchVault citations={draftCitations} activeCitationId={activeCitationId} />
          ) : graphData ? (
            <div className="w-full h-full">
              {/* Legend/Controls Overlay */}
              <div className="absolute top-4 right-4 z-10 bg-white/90 backdrop-blur-sm p-3 rounded-lg border border-slate-200 shadow-sm text-xs space-y-2">
                <div className="font-semibold text-slate-700 mb-1">Graph Legend</div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                  <span className="text-slate-600">Cited Entity</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-slate-400"></span>
                  <span className="text-slate-600">Related Entity</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-orange-500"></span>
                  <span className="text-slate-600">Hovered</span>
                </div>
                <div className="mt-2 pt-2 border-t border-slate-100 text-[10px] text-slate-400">
                  {graphData.stats?.total_nodes || 0} Nodes • {graphData.stats?.total_edges || 0} Edges
                </div>
              </div>

              {/* Graph Component */}
              <KnowledgeGraph
                data={graphData}
                focusedNodeId={highlightedNode}
                regimeMode={regime}
              />
            </div>
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 gap-4">
              <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center">
                <Scale className="w-8 h-8 opacity-20" />
              </div>
              <p>Ask a question to visualize legal connections</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

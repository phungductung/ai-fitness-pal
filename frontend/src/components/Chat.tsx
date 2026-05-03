"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Loader2, Plus, ShieldCheck, ShieldX } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sender?: string;
  attachment?: {
    name: string;
    type: string;
    serverPath: string;
  } | null;
}

interface AttachedFile {
  name: string;
  type: string;
  serverPath: string;
}

interface InterruptData {
  type: string;
  thread_id: string;
  question: string;
  tool_calls: any[];
}

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [attachedFile, setAttachedFile] = useState<AttachedFile | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [pendingInterrupt, setPendingInterrupt] = useState<InterruptData | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', file.type.includes('pdf') ? 'pdf' : 'image');

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (data.status === 'success') {
        setAttachedFile({
          name: file.name,
          type: file.type,
          serverPath: data.filename
        });
      }
    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setIsUploading(false);
      e.target.value = ""; // Reset input so the same file can be selected again
    }
  };

  const handleNewChat = React.useCallback(async () => {
    setMessages([]);
    setInput('');
    setIsLoading(false);
    setAttachedFile(null);
    setPendingInterrupt(null);
    // Request a fresh thread_id from the backend
    try {
      const res = await fetch('http://localhost:8000/chat/new', { method: 'POST' });
      const data = await res.json();
      setThreadId(data.thread_id);
    } catch {
      setThreadId(null);
    }
  }, []);

  useEffect(() => {
    const handleExternalNewChat = () => handleNewChat();
    window.addEventListener('new-chat', handleExternalNewChat);
    return () => window.removeEventListener('new-chat', handleExternalNewChat);
  }, [handleNewChat]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, pendingInterrupt]);

  // --- Handle human-in-the-loop approval/rejection ---
  const handleInterruptResponse = async (approved: boolean) => {
    if (!pendingInterrupt?.thread_id) return;

    setPendingInterrupt(null);
    setIsLoading(true);

    // Add a system-style message showing what the user decided
    const decisionMsg: ChatMessage = {
      role: 'user' as const,
      content: approved ? '✅ Approved' : '❌ Rejected',
    };
    setMessages(prev => [...prev, decisionMsg]);

    try {
      const response = await fetch('http://localhost:8000/chat/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: pendingInterrupt.thread_id,
          approved,
        }),
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split(/\n\n|\r\n\r\n/);
        buffer = parts.pop() || '';

        for (const part of parts) {
          if (!part.trim()) continue;

          const lines = part.split('\n');
          let event = 'message';
          let data = '';

          for (const line of lines) {
            const cleanLine = line.trim();
            if (cleanLine.startsWith('event: ')) event = cleanLine.replace('event: ', '').trim();
            else if (cleanLine.startsWith('data: ')) data = cleanLine.replace('data: ', '').trim();
          }

          if (data === 'end' || event === 'done') {
            setIsLoading(false);
            window.dispatchEvent(new CustomEvent('data-updated'));
            continue;
          }

          if (data) {
            try {
              const parsedData = JSON.parse(data);
              const sender = parsedData.sender || 'assistant';

              if (event === 'token' && parsedData.token) {
                setMessages(prev => {
                  const lastMsg = prev[prev.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant' && lastMsg.sender === sender) {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = { ...lastMsg, content: lastMsg.content + parsedData.token };
                    return newMessages;
                  }
                  return [...prev, { role: 'assistant', content: parsedData.token, sender }];
                });
              } else if (event === 'message' && parsedData.content) {
                setMessages(prev => {
                  const lastMsg = prev[prev.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant' && lastMsg.sender === sender) {
                    const newMessages = [...prev];
                    if (parsedData.content.length >= lastMsg.content.length - 5) {
                      newMessages[newMessages.length - 1] = { ...lastMsg, content: parsedData.content };
                    }
                    return newMessages;
                  }
                  return [...prev, { role: 'assistant', content: parsedData.content, sender }];
                });
              }
            } catch (e) {
              console.error("Error parsing resume response:", data, e);
            }
          }
        }
      }
    } catch (error) {
      console.error("Resume error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = { 
      role: 'user' as const, 
      content: input,
      attachment: attachedFile ? { ...attachedFile } : null 
    };
    const currentInput = input;
    const currentHistory = [...messages]; // Legacy: only used on first message if no threadId
    const currentFile = attachedFile;
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      console.log("Sending message to backend...");
      const payload: Record<string, any> = { 
        message: currentInput, 
        file_path: currentFile?.serverPath || null,
      };

      // Attach thread_id for persistent sessions
      if (threadId) {
        payload.thread_id = threadId;
      }

      // Only send history on the very first message (backwards-compat)
      if (!threadId) {
        payload.history = currentHistory;
      }
      
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      setAttachedFile(null);

      if (!response.body) {
        console.error("No response body received");
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        const parts = buffer.split(/\n\n|\r\n\r\n/);
        buffer = parts.pop() || ''; 
        
        for (const part of parts) {
          if (!part.trim()) continue;
          
          const lines = part.split('\n');
          let event = 'message';
          let data = '';
          
          for (const line of lines) {
            const cleanLine = line.trim();
            if (cleanLine.startsWith('event: ')) {
              event = cleanLine.replace('event: ', '').trim();
            } else if (cleanLine.startsWith('data: ')) {
              data = cleanLine.replace('data: ', '').trim();
            }
          }
          
          if (data === 'end' || event === 'done') {
            console.log("Stream ended");
            setIsLoading(false);
            window.dispatchEvent(new CustomEvent('data-updated'));
            continue;
          }

          // --- Handle thread_id assignment from backend ---
          if (event === 'thread') {
            try {
              const threadData = JSON.parse(data);
              if (threadData.thread_id) {
                setThreadId(threadData.thread_id);
                console.log("Thread ID set:", threadData.thread_id);
              }
            } catch (e) {
              console.error("Error parsing thread event:", data, e);
            }
            continue;
          }

          // --- Handle human-in-the-loop interrupt ---
          if (event === 'interrupt') {
            try {
              const interruptData = JSON.parse(data);
              setPendingInterrupt(interruptData);
              setIsLoading(false);
              console.log("Interrupt received:", interruptData);
            } catch (e) {
              console.error("Error parsing interrupt event:", data, e);
            }
            continue;
          }
          
          if (data) {
            try {
              const parsedData = JSON.parse(data);
              const sender = parsedData.sender === 'coach' ? 'coach' : 
                             parsedData.sender === 'nutrition' ? 'nutrition' : 
                             parsedData.sender || 'assistant';

              if (event === 'token' && parsedData.token) {
                setMessages(prev => {
                  const lastMsg = prev[prev.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant' && lastMsg.sender === sender) {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = {
                      ...lastMsg,
                      content: lastMsg.content + parsedData.token
                    };
                    return newMessages;
                  } else {
                    return [...prev, { role: 'assistant', content: parsedData.token, sender: sender }];
                  }
                });
              } else if (event === 'message' && parsedData.content) {
                setMessages(prev => {
                  const lastMsg = prev[prev.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant' && lastMsg.sender === sender) {
                    const newMessages = [...prev];
                    if (parsedData.content.length >= lastMsg.content.length - 5) {
                      newMessages[newMessages.length - 1] = {
                        ...lastMsg,
                        content: parsedData.content
                      };
                    }
                    return newMessages;
                  } else {
                    return [...prev, { role: 'assistant', content: parsedData.content, sender: sender }];
                  }
                });
              }
            } catch (e) {
              console.error("Error parsing JSON chunk:", data, e);
            }
          }
        }
      }
    } catch (error) {
      console.error("Chat error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full glass">
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button 
            onClick={handleNewChat}
            className="p-2 hover:bg-white/5 rounded-lg transition text-gray-400 hover:text-white"
            title="New Chat"
          >
            <Plus size={20} />
          </button>
          <h3 className="font-semibold text-lg">AI Chatbot</h3>
          {threadId && (
            <span className="text-[9px] text-gray-600 font-mono ml-1 hidden sm:inline" title={`Thread: ${threadId}`}>
              🔗 {threadId.slice(0, 8)}…
            </span>
          )}
        </div>
        <div className="flex -space-x-2">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center border-2 border-[#141414]">
            <Dumbbell size={14} className="text-black" />
          </div>
          <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center border-2 border-[#141414]">
            <Utensils size={14} className="text-white" />
          </div>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] p-3 rounded-2xl ${
              msg.role === 'user' 
                ? 'bg-primary text-black rounded-tr-none' 
                : 'bg-white/5 border border-white/10 rounded-tl-none'
            }`}>
              {msg.role === 'assistant' && (
                <div className="text-[10px] uppercase font-bold text-gray-400 mb-1 flex items-center gap-1">
                  {msg.sender === 'coach' ? <Dumbbell size={10} /> : <Utensils size={10} />}
                  {msg.sender}
                </div>
              )}
              <div className="text-sm markdown-content">
                {msg.attachment && (
                  <div className="mb-2">
                    {msg.attachment?.type?.startsWith('image/') ? (
                      <img 
                        src={`http://localhost:8000/${msg.attachment?.serverPath}`} 
                        alt="attachment" 
                        className="max-w-full rounded-lg border border-white/10 cursor-zoom-in hover:opacity-90 transition-opacity"
                        onClick={() => setPreviewImage(`http://localhost:8000/${msg.attachment?.serverPath}`)}
                      />
                    ) : (
                      <div className="flex items-center gap-2 p-2 bg-white/10 rounded-lg border border-white/10 w-fit">
                        <Paperclip size={14} className="text-primary" />
                        <span className="text-xs truncate max-w-[150px]">{msg.attachment.name}</span>
                      </div>
                    )}
                  </div>
                )}
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    img: ({ node, ...props }) => (
                      <img 
                        {...props} 
                        className="max-w-full rounded-lg border border-white/10 my-2 cursor-zoom-in hover:opacity-90 transition-opacity" 
                        onClick={() => setPreviewImage(typeof props.src === 'string' ? props.src : null)}
                      />
                    )
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        ))}

        {/* --- Human-in-the-Loop Confirmation Card --- */}
        {pendingInterrupt && (
          <div className="flex justify-start">
            <div className="max-w-[85%] p-4 rounded-2xl rounded-tl-none bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-amber-500/30 backdrop-blur-sm">
              <div className="text-[10px] uppercase font-bold text-amber-400 mb-2 flex items-center gap-1">
                <ShieldCheck size={12} />
                Confirmation Required
              </div>
              <div className="text-sm markdown-content mb-4">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {pendingInterrupt.question}
                </ReactMarkdown>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleInterruptResponse(true)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-400 rounded-xl text-xs font-semibold transition-all duration-200 hover:scale-105"
                >
                  <ShieldCheck size={14} />
                  Approve
                </button>
                <button
                  onClick={() => handleInterruptResponse(false)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 text-red-400 rounded-xl text-xs font-semibold transition-all duration-200 hover:scale-105"
                >
                  <ShieldX size={14} />
                  Reject
                </button>
              </div>
            </div>
          </div>
        )}

        {isLoading && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
          <div className="flex justify-start">
            <div className="bg-white/5 border border-white/10 p-4 rounded-2xl rounded-tl-none flex gap-1 items-center">
              <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></div>
              <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></div>
              <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"></div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-white/10">
        {attachedFile && (
          <div className="mb-2 flex items-center gap-2 p-2 bg-white/5 rounded-lg border border-white/10 w-fit">
            <Paperclip size={14} className="text-primary" />
            <span className="text-xs text-gray-300 truncate max-w-[200px]">{attachedFile.name}</span>
            <button 
              onClick={() => setAttachedFile(null)}
              className="ml-1 text-gray-500 hover:text-white"
            >
              <Plus size={14} className="rotate-45" />
            </button>
          </div>
        )}
        <div className="relative">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
            accept="image/*,.pdf"
          />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={isUploading ? "Uploading file..." : "Ask about your workout, nutrition, or PRs..."}
            disabled={isUploading || !!pendingInterrupt}
            className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-12 focus:ring-1 focus:ring-primary focus:border-transparent outline-none transition-all disabled:opacity-50"
          />
          <button 
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition disabled:opacity-50"
          >
            {isUploading ? <Loader2 size={20} className="animate-spin" /> : <Paperclip size={20} />}
          </button>
          <button 
            onClick={handleSend}
            disabled={isLoading || isUploading || !!pendingInterrupt || (!input.trim() && !attachedFile)}
            className={`absolute right-3 top-1/2 -translate-y-1/2 transition-all duration-200 ${
              isLoading || isUploading || !!pendingInterrupt || (!input.trim() && !attachedFile) ? 'text-gray-600 cursor-not-allowed scale-95' : 'text-primary hover:text-white scale-100 hover:scale-110'
            }`}
          >
            <Send size={20} />
          </button>
        </div>
        <p className="text-[10px] text-gray-500 mt-2 text-center">
          Multimodal support: Drop a supplement image or training PDF to analyze.
        </p>
      </div>

      {/* Image Preview Modal */}
      {previewImage && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm p-4 animate-fade-in"
          onClick={() => setPreviewImage(null)}
        >
          <button 
            className="absolute top-4 right-4 p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors"
            onClick={() => setPreviewImage(null)}
          >
            <Plus size={24} className="rotate-45" />
          </button>
          <img 
            src={previewImage} 
            alt="Preview" 
            className="max-w-full max-h-full object-contain rounded-lg shadow-2xl animate-zoom-in"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}

function Dumbbell({ size, className }: { size: number; className?: string }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="m6.5 6.5 11 11"/><path d="m10 10 5.5 5.5"/><path d="m3 21 8-8"/><path d="m9 22 10-10"/><path d="m2 19 10-10"/><path d="m14 11 8 8"/><path d="m15 10 7-7"/><path d="m19 2 3 3"/></svg>;
}

function Utensils({ size, className }: { size: number; className?: string }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><path d="M7 2v20"/><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"/></svg>;
}

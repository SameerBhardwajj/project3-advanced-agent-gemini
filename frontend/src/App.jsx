import { useEffect, useState } from "react";

const API = "http://localhost:8000";
const headers = token => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${token}`,
});

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [user, setUser] = useState(null);
  const [email, setEmail] = useState("employee@example.com");
  const [password, setPassword] = useState("demo-password");
  const [chats, setChats] = useState([]);
  const [chatId, setChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => { if (token) { loadMe(); loadChats(); } }, [token]);

  async function loadMe() {
    const r = await fetch(`${API}/api/auth/me`, { headers: headers(token) });
    if (r.ok) setUser(await r.json()); else logout();
  }
  async function loadChats() {
    const r = await fetch(`${API}/api/chats`, { headers: headers(token) });
    if (r.ok) setChats(await r.json());
  }
  async function login(e) {
    e.preventDefault(); setError("");
    const r = await fetch(`${API}/api/auth/login`, {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({email, password})
    });
    const d = await r.json();
    if (!r.ok) return setError(d.detail || "Login failed.");
    localStorage.setItem("token", d.access_token);
    setToken(d.access_token); setUser(d.user);
  }
  function logout() {
    localStorage.removeItem("token"); setToken(""); setUser(null);
    setChats([]); setMessages([]); setChatId(null);
  }
  async function newChat() {
    const r = await fetch(`${API}/api/chats`, {
      method:"POST", headers:headers(token), body:JSON.stringify({title:"New chat"})
    });
    const c = await r.json(); setChats(x=>[c,...x]); setChatId(c.id);
    setMessages([]); setMeta(null);
  }
  async function openChat(id) {
    const r = await fetch(`${API}/api/chats/${id}/messages`, {headers:headers(token)});
    if (r.ok) { setChatId(id); setMessages(await r.json()); setMeta(null); }
  }
  async function send(e) {
    e.preventDefault();
    const text=input.trim(); if(!text||loading) return;
    setLoading(true); setError("");
    try {
      let id=chatId;
      if(!id){
        const r=await fetch(`${API}/api/chats`,{method:"POST",headers:headers(token),body:JSON.stringify({title:text.slice(0,60)})});
        const c=await r.json(); id=c.id; setChatId(id); setChats(x=>[c,...x]);
      }
      setMessages(m=>[...m,{role:"user",content:text}]); setInput("");
      const r=await fetch(`${API}/api/chats/${id}/messages`,{
        method:"POST",headers:headers(token),body:JSON.stringify({message:text})
      });
      const d=await r.json();
      if(!r.ok) throw Error(d.detail||"Agent failed.");
      setMessages(m=>[...m,{role:"assistant",content:d.answer}]);
      setMeta(d); loadChats();
    } catch(e){ setError(e.message); } finally { setLoading(false); }
  }

  if(!token) return <div className="login"><form onSubmit={login}>
    <small>PROJECT 3</small><h1>Advanced Agent</h1>
    <p>Tools + authentication + authorization + memory + multi-step tasks</p>
    <input value={email} onChange={e=>setEmail(e.target.value)} placeholder="Email"/>
    <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password"/>
    <button>Login</button>
    <small>Employee: employee@example.com / demo-password<br/>Manager: manager@example.com / demo-password</small>
    {error&&<div className="error">{error}</div>}
  </form></div>;

  return <div className="app">
    <aside>
      <small>PROJECT 3</small><h2>Advanced Agent</h2>
      <div className="user">{user?.name}<br/><small>{user?.email} · {user?.role}</small></div>
      <button onClick={newChat}>+ New chat</button><h4>Chat history</h4>
      {chats.map(c=><button className="history" key={c.id} onClick={()=>openChat(c.id)}>{c.title}</button>)}
      <button className="logout" onClick={logout}>Logout</button>
    </aside>
    <main>
      <header><b>Company Advanced Agent</b><span>{user?.role}</span></header>
      <section className="messages">
        {!messages.length&&<div className="empty"><h2>Try a multi-step task</h2>
          <p>“Check my leave balance and request leave from 2026-09-01 to 2026-09-03 for a family trip.”</p>
          <p>“Remember that I prefer concise answers.”</p></div>}
        {messages.map((m,i)=><div className={`row ${m.role}`} key={i}><div className="bubble"><b>{m.role==="user"?"You":"Agent"}</b><br/>{m.content}</div></div>)}
        {loading&&<div className="bubble">Agent is planning and using tools…</div>}
      </section>
      {meta&&<section className="meta">
        <b>Intent:</b> {meta.intent} &nbsp;
        <b>Memory:</b> {meta.memory_used?.join(", ")||"none"}<br/>
        <b>Actions:</b> {meta.actions?.map((a,i)=><span className={a.status} key={i}>{a.tool}:{a.status}</span>)}
      </section>}
      {error&&<div className="error">{error}</div>}
      <form className="composer" onSubmit={send}>
        <textarea value={input} onChange={e=>setInput(e.target.value)} placeholder="Ask the agent..." rows="3"/>
        <button disabled={loading}>Send</button>
      </form>
    </main>
  </div>;
}
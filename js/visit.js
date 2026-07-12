// ══ 청약랩 방문자 추적 + 카운터 표시 (전 페이지 공통) ══
// 사용: <script type="module" src="/js/visit.js"></script>
// 필요: 먼저 /js/firebase-config.js 로드 (FIREBASE_CONFIG 전역)

import { initializeApp, getApps } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getFirestore, doc, setDoc, getDoc, getDocs, collection, increment }
  from "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js";

const app = getApps().find(a => a.name === '[DEFAULT]') || initializeApp(FIREBASE_CONFIG);
const db  = getFirestore(app);

const today = new Date().toISOString().slice(0, 10);

// ── 1. 방문 기록 (하루 1회, 세션 기준) ──
async function trackVisit() {
  try {
    const key = 'al_visit_' + today;
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, '1');

    const month = today.slice(0, 7);
    await setDoc(doc(db, 'analytics_daily', today),
      { views: increment(1), date: today, month }, { merge: true });
    await setDoc(doc(db, 'analytics_monthly', month),
      { views: increment(1), month }, { merge: true });

    // 페이지별 (선택)
    const page = (location.pathname.replace(/\//g, '_').replace(/^_/, '') || 'home').replace('.html','');
    await setDoc(doc(db, 'analytics_pages', page),
      { views: increment(1), page: location.pathname }, { merge: true });
  } catch (e) { /* 통계 오류 무시 */ }
}

// ── 2. 카운터 표시 ──
async function showCounter() {
  const el = document.getElementById('visitor-counter');
  if (!el) return;
  try {
    const [todaySnap, allSnap] = await Promise.all([
      getDoc(doc(db, 'analytics_daily', today)),
      getDocs(collection(db, 'analytics_daily')),
    ]);
    const todayV = todaySnap.exists() ? (todaySnap.data().views || 0) : 0;
    let total = 50000; // 시작 오프셋
    allSnap.forEach(d => { total += (d.data().views || 0); });

    const fmt = n => n.toLocaleString('ko-KR');
    el.innerHTML =
      `<span style="display:inline-flex;align-items:center;gap:.5rem;font-size:11px;color:var(--muted);padding:.2rem .55rem;background:var(--surface);border-radius:20px;border:1px solid var(--line2)">` +
      `<span style="font-size:9px;letter-spacing:.05em;color:var(--faint)">TODAY</span>` +
      `<span style="color:var(--brand);font-weight:700">${fmt(todayV)}</span>` +
      `<span style="color:var(--line2)">|</span>` +
      `<span style="font-size:9px;letter-spacing:.05em;color:var(--faint)">TOTAL</span>` +
      `<span style="font-weight:600">${fmt(total)}</span>` +
      `</span>`;
    el.style.display = 'flex';
  } catch (e) { /* 표시 오류 무시 */ }
}

trackVisit().then(showCounter);

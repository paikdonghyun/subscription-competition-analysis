// ══ 청약랩 ApplyLab 공통 JS ══
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getAuth, onAuthStateChanged, signOut, createUserWithEmailAndPassword,
         signInWithEmailAndPassword, updateProfile } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";
import { getFirestore, doc, setDoc, getDoc, updateDoc, increment,
         serverTimestamp, collection, addDoc } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js";

// ── Firebase 초기화 ──
const app = initializeApp(FIREBASE_CONFIG);
const auth = getAuth(app);
const db   = getFirestore(app);

// ── 전역 상태 ──
window.AL = { auth, db, user: null, userDoc: null };

// ── 방문자 추적 ──
async function trackVisit() {
  try {
    const sessionKey = 'al_session_' + new Date().toDateString();
    if (sessionStorage.getItem(sessionKey)) return;
    sessionStorage.setItem(sessionKey, '1');

    const today = new Date().toISOString().slice(0, 10);
    const month = today.slice(0, 7);
    const week  = getWeekKey();
    const page  = location.pathname.replace(/\/$/, '') || '/';

    // 일별 통계
    await setDoc(doc(db, 'analytics_daily', today), {
      views: increment(1), date: today, month, week
    }, { merge: true });
    // 월별
    await setDoc(doc(db, 'analytics_monthly', month), {
      views: increment(1), month
    }, { merge: true });
    // 페이지별
    const safeKey = page.replace(/\//g, '_').replace(/^_/, '') || 'home';
    await setDoc(doc(db, 'analytics_pages', safeKey), {
      views: increment(1), page
    }, { merge: true });
  } catch(e) { /* 통계 오류는 무시 */ }
}
function getWeekKey() {
  const d = new Date();
  const jan = new Date(d.getFullYear(), 0, 1);
  const week = Math.ceil(((d - jan) / 86400000 + jan.getDay() + 1) / 7);
  return `${d.getFullYear()}-W${String(week).padStart(2,'0')}`;
}

// ── 인증 상태 감지 & 네비게이션 렌더 ──
function renderNav(user, userDoc) {
  const right = document.getElementById('gnav-right');
  if (!right) return;
  if (user) {
    const name = userDoc?.displayName || user.email.split('@')[0];
    const initial = name[0].toUpperCase();
    const isAdmin = userDoc?.role === 'admin';
    right.innerHTML = `
      <div class="gnav-dropdown">
        <div class="gnav-user" style="cursor:pointer;padding:.25rem .5rem;border-radius:var(--r);transition:background .12s" onmouseenter="this.style.background='var(--bg2)'" onmouseleave="this.style.background=''">
          <div class="gnav-avatar">${initial}</div>
          <span>${name}</span>
          ${isAdmin ? '<span class="badge badge-red" style="font-size:9px">관리자</span>' : ''}
          <span style="font-size:10px;color:var(--ink4)">▾</span>
        </div>
        <div class="gnav-dropdown-menu">
          <a class="gnav-dropdown-item" href="/mypage.html">마이페이지</a>
          ${isAdmin ? '<a class="gnav-dropdown-item badge-red" href="/admin/" style="color:var(--red)">⚙ 관리자</a><hr style="border:none;border-top:1px solid var(--bg3);margin:.25rem 0">' : ''}
          <a class="gnav-dropdown-item danger" href="#" onclick="AL.logout();return false">로그아웃</a>
        </div>
      </div>`;
  } else {
    right.innerHTML = `
      <a href="/login.html" class="gnav-btn outline">로그인</a>
      <a href="/login.html#register" class="gnav-btn solid">회원가입</a>`;
  }
}

onAuthStateChanged(auth, async (user) => {
  window.AL.user = user;
  if (user) {
    const snap = await getDoc(doc(db, 'users', user.uid));
    window.AL.userDoc = snap.exists() ? snap.data() : null;
    // 마지막 로그인 업데이트
    if (snap.exists()) {
      await updateDoc(doc(db, 'users', user.uid), { lastLoginAt: serverTimestamp() });
    }
  } else {
    window.AL.userDoc = null;
  }
  renderNav(user, window.AL.userDoc);
  // 페이지별 auth guard
  const path = location.pathname;
  if (path.includes('/admin/') && window.AL.userDoc?.role !== 'admin') {
    location.href = '/login.html';
  }
  if (path.includes('/mypage') && !user) {
    location.href = '/login.html';
  }
});

// ── 로그아웃 ──
window.AL.logout = async () => {
  await signOut(auth);
  location.href = '/';
};

// ── 회원가입 ──
window.AL.register = async (email, password, name) => {
  const cred = await createUserWithEmailAndPassword(auth, email, password);
  await updateProfile(cred.user, { displayName: name });
  const role = email === ADMIN_EMAIL ? 'admin' : 'user';
  await setDoc(doc(db, 'users', cred.user.uid), {
    uid: cred.user.uid, email, displayName: name, role,
    createdAt: serverTimestamp(), lastLoginAt: serverTimestamp(),
    status: 'active'
  });
  return cred.user;
};

// ── 로그인 ──
window.AL.login = async (email, password) => {
  const cred = await signInWithEmailAndPassword(auth, email, password);
  return cred.user;
};

// ── 방문자 추적 실행 ──
trackVisit();

export { auth, db };

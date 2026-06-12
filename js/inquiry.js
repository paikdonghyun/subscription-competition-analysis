// ══════════════════════════════════════════════════
//  청약랩 ApplyLab — 문의 & 수정요청 모듈
//  모든 공개 페이지 푸터에 CTA 버튼 + 접수 모달을 삽입
//  접수 내역은 Firestore 'inquiries' 컬렉션에 저장 (관리자만 열람)
// ══════════════════════════════════════════════════
import { initializeApp, getApps } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getFirestore, collection, addDoc, serverTimestamp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js";

// index.html 등 기본 앱이 이미 초기화된 페이지와 충돌하지 않도록 별도 이름의 앱 사용
const app = getApps().find(a => a.name === 'inquiryApp')
  || initializeApp(FIREBASE_CONFIG, 'inquiryApp');
const db = getFirestore(app);

const TYPES = [
  { v: 'data',    label: '데이터 오류 신고' },
  { v: 'feature', label: '기능 · 수정 요청' },
  { v: 'etc',     label: '일반 문의' },
];

/* ── 푸터 CTA + 모달 주입 ── */
function inject() {
  const footer = document.querySelector('footer');
  if (!footer) return;

  // CTA 배너 (푸터 최상단)
  const cta = document.createElement('div');
  cta.innerHTML = `
    <div style="max-width:1400px;margin:0 auto 1.25rem;text-align:center;padding-bottom:1.25rem;border-bottom:1px solid rgba(255,255,255,.08)">
      <div style="font-family:'Noto Serif KR',serif;font-size:.95rem;color:#e4e4e7;font-weight:600;margin-bottom:.25rem">
        데이터 오류를 발견하셨거나 필요한 기능이 있으신가요?
      </div>
      <div style="font-size:11.5px;color:#71717a;margin-bottom:.875rem">
        보내주신 의견은 관리자가 직접 확인하고 빠르게 반영합니다
      </div>
      <button id="inq-open" style="display:inline-flex;align-items:center;gap:.5rem;background:#1d4ed8;color:#fff;border:none;
        padding:.6rem 1.5rem;border-radius:24px;font-size:13.5px;font-weight:500;cursor:pointer;
        font-family:'Noto Sans KR',sans-serif;box-shadow:0 2px 10px rgba(29,78,216,.4);transition:all .15s">
        💬 문의 &amp; 수정요청
      </button>
    </div>`;
  footer.insertBefore(cta, footer.firstChild);
  const btn = cta.querySelector('#inq-open');
  btn.onmouseenter = () => { btn.style.background = '#1e40af'; btn.style.transform = 'translateY(-1px)'; };
  btn.onmouseleave = () => { btn.style.background = '#1d4ed8'; btn.style.transform = ''; };
  btn.onclick = openModal;

  // 모달
  const wrap = document.createElement('div');
  wrap.id = 'inq-modal-bg';
  wrap.style.cssText = 'position:fixed;inset:0;background:rgba(24,24,27,.5);z-index:300;display:none;align-items:flex-start;justify-content:center;padding:4rem 1rem 2rem;overflow-y:auto';
  wrap.innerHTML = `
    <div style="background:#fff;border-radius:12px;max-width:520px;width:100%;padding:1.5rem;box-shadow:0 10px 40px rgba(0,0,0,.2);font-family:'Noto Sans KR',sans-serif">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:.25rem">
        <div style="font-family:'Noto Serif KR',serif;font-size:1.05rem;font-weight:600;color:#18181b">문의 &amp; 수정요청</div>
        <button id="inq-close" style="border:none;background:#f3f4f6;color:#71717a;width:28px;height:28px;border-radius:50%;cursor:pointer;font-size:14px">✕</button>
      </div>
      <div style="font-size:12px;color:#a1a1aa;margin-bottom:1.1rem">접수된 내용은 관리자만 확인할 수 있습니다.</div>

      <label style="display:block;font-size:11px;font-family:'IBM Plex Mono',monospace;letter-spacing:.06em;color:#a1a1aa;margin-bottom:.3rem">유형</label>
      <div id="inq-types" style="display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:1rem">
        ${TYPES.map((t,i)=>`<button data-v="${t.v}" class="inq-type" style="font-size:12px;padding:.4rem .9rem;border-radius:20px;cursor:pointer;
          border:1.5px solid ${i===0?'#1d4ed8':'#e5e7eb'};background:${i===0?'#eff6ff':'#fff'};color:${i===0?'#1d4ed8':'#71717a'};font-family:inherit">${t.label}</button>`).join('')}
      </div>

      <label style="display:block;font-size:11px;font-family:'IBM Plex Mono',monospace;letter-spacing:.06em;color:#a1a1aa;margin-bottom:.3rem">내용 <span style="color:#dc2626">*</span></label>
      <textarea id="inq-content" rows="5" maxlength="2000" placeholder="예) 미분양 현황에서 ○○단지 미분양 수치가 실제와 다릅니다 / △△ 기능을 추가해 주세요"
        style="width:100%;box-sizing:border-box;background:#f3f4f6;border:1.5px solid #e5e7eb;border-radius:8px;padding:.65rem .8rem;font-size:13px;font-family:inherit;color:#3f3f46;outline:none;resize:vertical;margin-bottom:1rem"></textarea>

      <label style="display:block;font-size:11px;font-family:'IBM Plex Mono',monospace;letter-spacing:.06em;color:#a1a1aa;margin-bottom:.3rem">회신 받을 연락처 <span style="color:#d4d4d8">(선택 · 이메일 또는 전화번호)</span></label>
      <input id="inq-contact" type="text" maxlength="100" placeholder="answer@example.com"
        style="width:100%;box-sizing:border-box;background:#f3f4f6;border:1.5px solid #e5e7eb;border-radius:8px;padding:.55rem .8rem;font-size:13px;font-family:inherit;color:#3f3f46;outline:none;margin-bottom:1.25rem">
      <input id="inq-hp" type="text" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px" aria-hidden="true">

      <div style="display:flex;gap:.5rem;justify-content:flex-end;align-items:center">
        <span id="inq-msg" style="font-size:12px;margin-right:auto"></span>
        <button id="inq-cancel" style="font-size:13px;padding:.55rem 1.1rem;border-radius:8px;border:1.5px solid #e5e7eb;background:#fff;color:#71717a;cursor:pointer;font-family:inherit">취소</button>
        <button id="inq-submit" style="font-size:13px;font-weight:500;padding:.55rem 1.4rem;border-radius:8px;border:none;background:#1d4ed8;color:#fff;cursor:pointer;font-family:inherit">접수하기</button>
      </div>
    </div>`;
  document.body.appendChild(wrap);

  let selType = TYPES[0].v;
  wrap.querySelectorAll('.inq-type').forEach(b => b.onclick = () => {
    selType = b.dataset.v;
    wrap.querySelectorAll('.inq-type').forEach(x => {
      const on = x.dataset.v === selType;
      x.style.borderColor = on ? '#1d4ed8' : '#e5e7eb';
      x.style.background  = on ? '#eff6ff' : '#fff';
      x.style.color       = on ? '#1d4ed8' : '#71717a';
    });
  });

  const close = () => { wrap.style.display = 'none'; document.body.style.overflow = ''; };
  wrap.querySelector('#inq-close').onclick = close;
  wrap.querySelector('#inq-cancel').onclick = close;
  wrap.addEventListener('click', e => { if (e.target === wrap) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

  wrap.querySelector('#inq-submit').onclick = async () => {
    const $msg = wrap.querySelector('#inq-msg');
    const $btn = wrap.querySelector('#inq-submit');
    const content = wrap.querySelector('#inq-content').value.trim();
    const contact = wrap.querySelector('#inq-contact').value.trim();
    if (wrap.querySelector('#inq-hp').value) return;                       // 봇 차단
    if (content.length < 5) { $msg.style.color = '#dc2626'; $msg.textContent = '내용을 5자 이상 입력해 주세요.'; return; }

    $btn.disabled = true; $btn.style.opacity = '.6';
    $msg.style.color = '#71717a'; $msg.textContent = '접수 중…';
    try {
      await addDoc(collection(db, 'inquiries'), {
        type: selType,
        content,
        contact: contact || null,
        page: location.pathname + location.search,
        status: 'new',
        createdAt: serverTimestamp(),
        ua: navigator.userAgent.slice(0, 200)
      });
      $msg.style.color = '#16a34a'; $msg.textContent = '✓ 접수되었습니다. 감사합니다!';
      wrap.querySelector('#inq-content').value = '';
      wrap.querySelector('#inq-contact').value = '';
      setTimeout(close, 1400);
    } catch (e) {
      $msg.style.color = '#dc2626';
      $msg.textContent = '접수에 실패했습니다. 잠시 후 다시 시도해 주세요.';
    } finally {
      $btn.disabled = false; $btn.style.opacity = '';
    }
  };
}

function openModal() {
  const wrap = document.getElementById('inq-modal-bg');
  wrap.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  wrap.querySelector('#inq-msg').textContent = '';
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', inject);
else inject();

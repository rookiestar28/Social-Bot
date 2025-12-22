LOGIN_CHECK = "text='Log in'"
LOGIN_BTN_LANDING = "a[href='/login']"
USERNAME_INPUT = "input[name='username']"
PASSWORD_INPUT = "input[name='password']"
LOGIN_SUBMIT = "div[role='button']:has-text('Log in'), div[role='button']:has-text('登入')"


FEED_ROOT = "div[role='main']"
POST_ARTICLE = "div[data-pressable-container='true'], div[role='article']" 
POST_ARTICLE = "div[data-pressable-container='true'], div[role='article']" 
POST_CONTENT_TEXT = "div[data-ad-preview='message'] span[dir='auto'], div[dir='auto'], span[dir='auto']"


REPLY_BUTTON = "div[role='button']:has(svg[aria-label='Reply']), div[role='button']:has(svg[aria-label='回覆']), div[role='button']:has(svg[aria-label='留言']), div[role='button']:text-is('Comment'), div[role='button']:text-is('留言')"

REPLY_MODAL = "div[role='dialog']"
NEW_THREAD_MODAL_TITLE = "div[role='dialog'] h1:has-text('新串文'), div[role='dialog'] h1:has-text('New thread'), div[role='dialog'] span:has-text('新串文')"
REPLY_MODAL_INDICATOR = "div[role='dialog'] div[role='textbox'][aria-placeholder*='Reply'], div[role='dialog'] div[role='textbox'][aria-placeholder*='回覆']"

REPLY_INPUT = "div[role='textbox'][aria-placeholder*='Reply'], div[role='textbox'][aria-placeholder*='回覆'], div[role='textbox'][aria-placeholder*='留言']"
REPLY_SEND_BTN = "div[role='button'][aria-label='Post'], div[role='button'][aria-label='Send'], div[role='button'][aria-label='發佈'], div[role='button'][aria-label='發布'], div[role='button'][aria-label='發送'], div[role='button']:has(svg)"


CLOSE_MODAL_BTN = "div[role='dialog'] div[role='button']:has(svg[aria-label='Close']), div[role='dialog'] div[role='button']:has(svg[aria-label='關閉'])"
DISCARD_MENU_BTN = "div[role='button']:has-text('Discard'), div[role='button']:has-text('捨棄')" # 有時候關閉會問是否捨棄

# --- Instagram Selectors ---
IG_NAV_HOME = "svg[aria-label='Home'], svg[aria-label='首頁']"
IG_POST_ARTICLE = "article, div[role='article']" 
IG_REPLY_BUTTON = "svg[aria-label*='Comment'], svg[aria-label*='留言'], svg[aria-label*='Reply'], button svg[aria-label*='Comment']"
IG_REPLY_TEXTAREA = "textarea, div[contenteditable='true'][role='textbox']"
# Broadened Post button selector to catch links/spans/divs without role='button'
IG_REPLY_POST_BTN = "div[role='button']:has-text('Post'), div[role='button']:has-text('發佈'), div[role='button']:has-text('發布'), button:has-text('Post'), button:has-text('發佈'), button:has-text('發布'), div:has-text('Post'), div:has-text('發佈'), div:has-text('發布'), span:has-text('Post'), span:has-text('發佈'), span:has-text('發布')"

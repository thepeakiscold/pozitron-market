#!/usr/bin/env node

/**
 * Pozitron Market - Reddit Automated Chrome Poster
 * Posts comments to Reddit posts directly via authenticated Chrome session
 */

const puppeteer = require('puppeteer-core');
const fs = require('fs');

function parseArgs() {
  const args = process.argv.slice(2);
  const params = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--url' && i + 1 < args.length) {
      params.url = args[++i];
    } else if (args[i] === '--text' && i + 1 < args.length) {
      params.text = args[++i];
    } else if (args[i] === '--text-file' && i + 1 < args.length) {
      params.textFile = args[++i];
    } else if (args[i] === '--cookies' && i + 1 < args.length) {
      params.cookies = args[++i];
    } else if (args[i] === '--username' && i + 1 < args.length) {
      params.username = args[++i];
    }
  }
  return params;
}

async function run() {
  const params = parseArgs();

  if (!params.url) {
    console.log(JSON.stringify({ success: false, error: 'URL parametresi eksik (--url)' }));
    process.exit(1);
  }

  let text = params.text || '';
  if (params.textFile && fs.existsSync(params.textFile)) {
    text = fs.readFileSync(params.textFile, 'utf-8');
  }

  if (!text || !text.trim()) {
    console.log(JSON.stringify({ success: false, error: 'Yorum metni bos olamaz' }));
    process.exit(1);
  }

  // Load cookies
  let cookies = [];
  const cookiesPath = params.cookies || '/tmp/test_reddit_cookies.json';
  if (fs.existsSync(cookiesPath)) {
    try {
      cookies = JSON.parse(fs.readFileSync(cookiesPath, 'utf-8'));
    } catch (e) {
      console.log(JSON.stringify({ success: false, error: 'Cerez dosyasi okunamadi: ' + e.message }));
      process.exit(1);
    }
  } else {
    console.log(JSON.stringify({ success: false, error: 'Cerez dosyasi bulunamadi: ' + cookiesPath }));
    process.exit(1);
  }

  function findChromeExecutable() {
    const candidates = [
      process.env.CHROME_PATH,
      '/opt/google/chrome/chrome',
      '/usr/bin/google-chrome-stable',
      '/usr/bin/google-chrome',
      '/usr/bin/chromium-browser',
      '/usr/bin/chromium',
      '/home/eyup/.local/bin/google-chrome-stable',
      '/home/eyup/.local/bin/google-chrome'
    ].filter(Boolean);

    for (const p of candidates) {
      if (fs.existsSync(p)) return p;
    }
    return null;
  }

  const chromePath = findChromeExecutable();
  if (!chromePath) {
    console.log(JSON.stringify({ success: false, error: 'Sistemde Google Chrome veya Chromium bulunamadi.' }));
    process.exit(1);
  }

  const isHeadless = Boolean(params.headless || process.env.HEADLESS === 'true' || (!process.env.DISPLAY && !process.env.WAYLAND_DISPLAY));
  const launchArgs = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-blink-features=AutomationControlled',
    '--window-size=1440,900',
    '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
  ];
  if (process.env.DISPLAY) {
    launchArgs.push('--window-position=-2400,-2400');
  }

  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: chromePath,
      headless: isHeadless ? 'new' : false,
      args: launchArgs
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });

    // Anti-detection stealth evasion
    await page.evaluateOnNewDocument(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    });

    // Set cookies
    await page.setCookie(...cookies);

    // Target post URL
    let targetUrl = params.url;
    if (!targetUrl.startsWith('http')) {
      targetUrl = 'https://www.reddit.com' + targetUrl;
    }

    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 35000 });
    await new Promise(r => setTimeout(r, 2000));

    // 1. Scroll down past post body to hydrate the comment area
    await page.evaluate(() => {
      const target = document.querySelector('comment-body-header, [data-testid="comments-feed"], shreddit-post');
      if (target) {
        target.scrollIntoView({ behavior: 'instant', block: 'end' });
      }
    });
    await new Promise(r => setTimeout(r, 1000));

    // 2. Locate the hydrated visible trigger button
    let triggerCoords = await page.evaluate(() => {
      const triggers = Array.from(document.querySelectorAll('faceplate-textarea-input[data-testid="trigger-button"]'));
      for (const t of triggers) {
        const r = t.getBoundingClientRect();
        if (r.width > 100 && r.height > 20) {
          t.scrollIntoView({ behavior: 'instant', block: 'center' });
          const r2 = t.getBoundingClientRect();
          return { x: r2.left + 50, y: r2.top + 20 };
        }
      }
      return null;
    });

    // Click trigger to expand comment composer
    if (triggerCoords) {
      await page.mouse.click(triggerCoords.x, triggerCoords.y);
      await new Promise(r => setTimeout(r, 1200));
    }

    // 3. Locate rich text editor
    const rteCoords = await page.evaluate(() => {
      const rte = document.querySelector('shreddit-composer div[slot="rte"][contenteditable="true"], shreddit-composer div[role="textbox"]');
      if (rte) {
        rte.scrollIntoView({ behavior: 'instant', block: 'center' });
        const r = rte.getBoundingClientRect();
        if (r.width > 100 && r.height > 20) {
          return { x: r.left + 50, y: r.top + 20 };
        }
      }
      return null;
    });

    if (!rteCoords) {
      await page.screenshot({ path: '/tmp/chrome_poster_error.png' });
      throw new Error('Yorum yazma alani (shreddit-composer RTE) bulunamadi.');
    }

    // Click inside RTE to focus
    await page.mouse.click(rteCoords.x, rteCoords.y);
    await new Promise(r => setTimeout(r, 400));

    // Type comment text line by line
    const lines = text.split('\n');
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line) {
        await page.keyboard.type(line, { delay: 10 });
      }
      if (i < lines.length - 1) {
        await page.keyboard.down('Shift');
        await page.keyboard.press('Enter');
        await page.keyboard.up('Shift');
      }
    }

    await new Promise(r => setTimeout(r, 800));

    // 3. Listen for network response of comment creation
    let commentApiResult = null;
    page.on('response', async (res) => {
      const u = res.url();
      if (u.includes('/create-comment') || u.includes('/api/comment')) {
        try {
          const body = await res.text();
          commentApiResult = { status: res.status(), body };
        } catch (e) {
          commentApiResult = { status: res.status() };
        }
      }
    });

    // 4. Find submit button coords and click
    const submitCoords = await page.evaluate(() => {
      const btn = document.querySelector('#comment-composer-submit-button, button[slot="submit-button"], shreddit-composer button[type="submit"]');
      if (btn) {
        const r = btn.getBoundingClientRect();
        if (r.width > 20 && r.height > 10) {
          return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
        }
      }
      return null;
    });

    if (!submitCoords) {
      await page.screenshot({ path: '/tmp/chrome_poster_error.png' });
      throw new Error('Yorum gonder (Comment) butonu bulunamadi.');
    }

    // Physical mouse click on submit button
    await page.mouse.click(submitCoords.x, submitCoords.y);

    // Also trigger element.click() as backup
    await page.evaluate(() => {
      const btn = document.querySelector('#comment-composer-submit-button, button[slot="submit-button"]');
      if (btn) btn.click();
    });

    // 5. Wait for submission response or comment to be posted
    let success = false;
    const startTime = Date.now();

    while (Date.now() - startTime < 15000) {
      if (commentApiResult && commentApiResult.status >= 200 && commentApiResult.status < 300) {
        success = true;
        break;
      }

      const targetUsername = (params.username || 'Aggravating_End_1105').toLowerCase();

      // Check if newly added comment appears in the DOM or composer cleared
      const domCheck = await page.evaluate((uname) => {
        const composer = document.querySelector('shreddit-composer div[role="textbox"]');
        const userComments = Array.from(document.querySelectorAll('shreddit-comment'));
        const hasUserComment = userComments.some(c => (c.getAttribute('author') || '').toLowerCase() === uname);
        const timeago = document.querySelector('faceplate-timeago[created-timestamp]');
        return {
          composerActive: !!composer,
          composerText: composer ? composer.innerText.trim() : '',
          hasUserComment: hasUserComment || !!timeago
        };
      }, targetUsername);

      if (domCheck.hasUserComment || (domCheck.composerActive && domCheck.composerText === '')) {
        success = true;
        break;
      }

      await new Promise(r => setTimeout(r, 800));
    }

    if (!success && commentApiResult && commentApiResult.status >= 400) {
      throw new Error(`Reddit API hata kodu verdi: HTTP ${commentApiResult.status} - ${commentApiResult.body || ''}`);
    }

    // Find comment permalink if available
    const targetUsername = (params.username || 'Aggravating_End_1105').toLowerCase();
    const postPermalink = await page.evaluate((uname) => {
      const comments = Array.from(document.querySelectorAll('shreddit-comment'));
      for (const c of comments) {
        if ((c.getAttribute('author') || '').toLowerCase() === uname) {
          return c.getAttribute('permalink') || '';
        }
      }
      return '';
    }, targetUsername);

    const finalPermalink = postPermalink ? ('https://www.reddit.com' + postPermalink) : targetUrl;

    console.log(JSON.stringify({
      success: true,
      url: targetUrl,
      permalink: finalPermalink,
      message: 'Yorum basariyla yayinlandi!'
    }));

    if (browser) {
      try {
        browser.process().kill('SIGKILL');
      } catch (e) {}
    }
    process.exit(0);

  } catch (err) {
    if (browser) {
      try {
        browser.process().kill('SIGKILL');
      } catch (e) {}
    }
    console.log(JSON.stringify({
      success: false,
      error: err.message || String(err)
    }));
    process.exit(1);
  }
}

run();

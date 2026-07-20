const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

// Usage: node scraper.js <URL>
const TARGET_URL = process.argv[2] || 'https://example.com';
const DOMAIN = new URL(TARGET_URL).hostname;

const DOWNLOAD_DIR = path.join(__dirname, 'scraped data (sarkarirresult.com)');

if (!fs.existsSync(DOWNLOAD_DIR)) {
    fs.mkdirSync(DOWNLOAD_DIR, { recursive: true });
}

const visitedUrls = new Set();
const pdfUrls = new Set();
const urlQueue = [TARGET_URL];

const downloadFile = (url, dest) => {
    return new Promise((resolve, reject) => {
        const file = fs.createWriteStream(dest);
        const client = url.startsWith('https') ? https : http;
        
        client.get(url, (response) => {
            if (response.statusCode === 301 || response.statusCode === 302) {
                return downloadFile(response.headers.location, dest).then(resolve).catch(reject);
            }
            
            if (response.statusCode !== 200) {
                return reject(new Error(`Failed to get '${url}' (${response.statusCode})`));
            }

            response.pipe(file);
            file.on('finish', () => {
                file.close(resolve);
            });
        }).on('error', (err) => {
            fs.unlink(dest, () => {});
            reject(err);
        });
    });
};

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
    console.log(`Starting headless scraper for ${TARGET_URL}`);
    
    // Launch puppeteer
    const browser = await puppeteer.launch({ 
        headless: "new",
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    // Block images, css, and media to speed up scraping significantly
    await page.setRequestInterception(true);
    page.on('request', (req) => {
        if (['image', 'stylesheet', 'font', 'media'].includes(req.resourceType())) {
            req.abort();
        } else {
            req.continue();
        }
    });

    while (urlQueue.length > 0) {
        const currentUrl = urlQueue.shift();

        // Strip hash fragments to avoid visiting the same page multiple times
        const cleanUrl = currentUrl.split('#')[0];

        if (visitedUrls.has(cleanUrl)) continue;
        visitedUrls.add(cleanUrl);

        try {
            console.log(`[${urlQueue.length} pages left in queue] Visiting: ${cleanUrl}`);
            await page.goto(cleanUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });

            const hrefs = await page.evaluate(() => {
                return Array.from(document.querySelectorAll('a')).map(a => a.href);
            });

            for (let href of hrefs) {
                if (!href || href.startsWith('javascript:')) continue;

                try {
                    const parsedUrl = new URL(href);
                    const cleanHref = href.split('#')[0];

                    if (parsedUrl.pathname.toLowerCase().endsWith('.pdf')) {
                        if (!pdfUrls.has(cleanHref)) {
                            pdfUrls.add(cleanHref);
                            console.log(`=> Found PDF: ${cleanHref}`);
                            const fileName = path.basename(parsedUrl.pathname);
                            
                            // Prefix with timestamp to prevent overwriting files with the same name
                            const uniqueFileName = `${Date.now()}_${fileName}`;
                            const destPath = path.join(DOWNLOAD_DIR, uniqueFileName);

                            if (!fs.existsSync(destPath)) {
                                console.log(`   Downloading ${uniqueFileName}...`);
                                await downloadFile(cleanHref, destPath);
                                await delay(500); // Polite delay between downloads
                            }
                        }
                    } else if (parsedUrl.hostname === DOMAIN && !visitedUrls.has(cleanHref) && !urlQueue.includes(cleanHref)) {
                        // Enqueue internal links, avoiding common static assets
                        if (!cleanHref.match(/\.(jpg|jpeg|png|gif|css|js|svg|ico|zip|rar)$/i)) {
                            urlQueue.push(cleanHref);
                        }
                    }
                } catch (e) {
                    // Ignore malformed URLs
                }
            }
        } catch (error) {
            console.error(`Failed to visit ${cleanUrl}: ${error.message}`);
        }

        await delay(1000); // Polite delay between pages to prevent getting rate-limited or IP banned
    }

    await browser.close();
    console.log(`Scraping complete. Found and downloaded ${pdfUrls.size} PDFs.`);
})();

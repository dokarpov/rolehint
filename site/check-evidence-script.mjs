import fs from 'node:fs';
import vm from 'node:vm';

// Fail before browser installation if the Evidence Inbox cannot even parse.
// The browser's usual DOM/HTTP tests then exercise the working script.
const markup = fs.readFileSync(new URL('../webapp/evidence.html', import.meta.url), 'utf8');
const blocks = [...markup.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)];
if (blocks.length !== 1) throw Error('Expected exactly one inline Evidence Inbox script');
new vm.Script(blocks[0][1], { filename: 'webapp/evidence.html#script' });
console.log('PASS Evidence Inbox inline JavaScript syntax');

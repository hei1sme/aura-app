// Script to convert SVG icon to PNG/ICO formats for Tauri
import sharp from 'sharp';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import pngToIco from 'png-to-ico';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const iconsDir = path.join(__dirname, '..', 'src-tauri', 'icons');
const svgPath = path.join(iconsDir, 'aura-icon.svg');

async function convertIcons() {
  console.log('Converting SVG icon to PNG formats...');
  
  const sizes = [
    { name: '32x32.png', size: 32 },
    { name: '128x128.png', size: 128 },
    { name: '128x128@2x.png', size: 256 },
    { name: 'icon.png', size: 512 },
  ];
  
  for (const { name, size } of sizes) {
    const outputPath = path.join(iconsDir, name);
    await sharp(svgPath)
      .resize(size, size)
      .png()
      .toFile(outputPath);
    console.log(`Created: ${name} (${size}x${size})`);
  }
  
  // Create ICO file from the 256x256 PNG
  console.log('Creating ICO file...');
  const pngBuffer = await sharp(svgPath)
    .resize(256, 256)
    .png()
    .toBuffer();
  
  const icoBuffer = await pngToIco([pngBuffer]);
  fs.writeFileSync(path.join(iconsDir, 'icon.ico'), icoBuffer);
  console.log('Created: icon.ico');
  
  console.log('All icons created successfully!');
}

convertIcons().catch(console.error);

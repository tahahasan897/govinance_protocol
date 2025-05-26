// scripts/updateSubgraph.js
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

// Load address from .env
require('dotenv').config({ path: path.join(__dirname, '..', 'necessities.env') });
const newAddress = process.env.CONTRACT_ADDRESS;
if (!newAddress) {
    console.error('❌ CONTRACT_ADDRESS not set in necessities.env');
    process.exit(1);
}

// Path to your subgraph manifest
const manifestPath = path.join(__dirname, '..', 'subgraph', 'subgraph.yaml');
const manifest = yaml.load(fs.readFileSync(manifestPath, 'utf8'));

// Update the address
manifest.dataSources[0].source.address = newAddress;
fs.writeFileSync(manifestPath, yaml.dump(manifest, { lineWidth: -1 }));
console.log(`✅ Updated subgraph.yaml to use address ${newAddress}`);

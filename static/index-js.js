// index-js.js

import {
    createWalletClient,
    custom,
    createPublicClient,
    parseEther,
    formatEther,
    defineChain
} from "https://esm.sh/viem";
import { walletContractAddress, tokenContractAddress, walletABI, tokenABI } from "./constants-js.js";

// manually define zkSync Sepolia
// const zksyncSepolia = {
//     id: 300,
//     name: "zkSync Sepolia Testnet",
//     network: "sepolia",
//     rpcUrls: {
//         default: {
//             http: ["https://sepolia.era.zksync.dev"]
//         }
//     },
//     nativeCurrency: {
//         name: "Ether",
//         symbol: "ETH",
//         decimals: 18
//     },
//     blockExplorers: {
//         default: {
//             name: "zkSync Explorer",
//             url: "https://sepolia.explorer.zksync.io"
//         }
//     }
// };

export const ethereumSepolia = defineChain({
    id: 11155111,
    name: "Ethereum Sepolia Testnet",
    nativeCurrency: {
        decimals: 18,
        name: "Sepolia Ether",
        symbol: "ETH",
    },
    rpcUrls: {
        default: {
            http: ["https://sepolia.infura.io/v3/252587a9d1de461093cfad5e7ec5d2f5"],
            webSocket: [],
        },
    },
    blockExplorers: {
        default: {
            name: "Etherscan",
            url: "https://sepolia.etherscan.io"
        }
    }
});

console.log("Loaded tokenABI:", tokenABI)

const connectButton = document.getElementById("connectButton");
const fundButton = document.getElementById("fundButton");
const ethAmountInput = document.getElementById("ethAmount");
const balanceButton = document.getElementById("balanceButton");
const withdrawButton = document.getElementById("withdrawButton");

const approveButton = document.getElementById("ApproveButton");
const approveAmountInput = document.getElementById("approveAmount");
const approveSpenderInput = document.getElementById("spenderAddress");

const transferButton = document.getElementById("transferButton");
const recipientInput = document.getElementById("recipientAddress");
const transferAmountInput = document.getElementById("transferAmount");

const transferFromButton = document.getElementById("TransferFromButton");
const fromAddressInput = document.getElementById("fromAddress");
const transferToAddressInput = document.getElementById("transferToAddress");
const valueAmountInput = document.getElementById("ValueAmount");

const allowanceButton = document.getElementById("AllowanceButton");
const ownerAddressInput = document.getElementById("ownerAddress");
const spenderAddressInput = document.querySelectorAll("#spenderAddress")[1]; // second spender input

const claimButton = document.getElementById("claimButton")

let walletClient, publicClient;

async function connect() {
    if (window.ethereum) {
        walletClient = createWalletClient({ transport: custom(window.ethereum) });
        await walletClient.requestAddresses();
        connectButton.textContent = "Connected!";
    } else {
        connectButton.textContent = "Please install MetaMask!";
    }
}

async function fund() {
    if (!window.ethereum) {
        connectButton.textContent = "Please install MetaMask!";
        return;
    }

    const ethAmount = ethAmountInput.value;
    walletClient = createWalletClient({ transport: custom(window.ethereum) });
    const [account] = await walletClient.requestAddresses();

    publicClient = createPublicClient({ transport: custom(window.ethereum) });
    const { request } = await publicClient.simulateContract({
        address: walletContractAddress,
        abi: walletABI,
        functionName: "fund",
        account,
        chain: ethereumSepolia,
        value: parseEther(ethAmount),
    });

    const txHash = await walletClient.writeContract(request);
    console.log("Fund tx hash:", txHash);
}

async function withdraw() {
    if (!window.ethereum) {
        connectButton.textContent = "Please install MetaMask!";
        return;
    }

    walletClient = createWalletClient({ transport: custom(window.ethereum) });
    const [account] = await walletClient.requestAddresses();

    publicClient = createPublicClient({ transport: custom(window.ethereum) });
    const { request } = await publicClient.simulateContract({
        address: walletContractAddress,
        abi: walletABI,
        functionName: "Withdraw", // must match exactly your ABI
        account,
        chain: ethereumSepolia,
    });

    const txHash = await walletClient.writeContract(request);
    console.log("Withdraw tx hash:", txHash);
}

async function getBalance() {
    if (!window.ethereum) {
        connectButton.textContent = "Please install MetaMask!";
        return;
    }

    publicClient = createPublicClient({ transport: custom(window.ethereum) });
    const balance = await publicClient.getBalance({
        address: walletContractAddress,
        chain: ethereumSepolia
    });
    console.log("Contract balance:", formatEther(balance), "ETH");
}

async function claim () {
    if (!window.ethereum) return alert("Connect wallet first!")
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' })
    const address = accounts[0]
    const res = await fetch("/interact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address })
    })
    const data = await res.json()
    alert(data.message)
}

async function approve() {
    if (!window.ethereum) return;
    walletClient = createWalletClient({ transport: custom(window.ethereum) });
    const [account] = await walletClient.requestAddresses();

    publicClient = createPublicClient({ transport: custom(window.ethereum) });
    const spender = approveSpenderInput.value;
    const amount = approveAmountInput.value;
    const { request } = await publicClient.simulateContract({
        address: tokenContractAddress,
        abi: tokenABI,
        functionName: "approve",
        args: [spender, parseEther(amount)],
        account,
        chain: ethereumSepolia,
    });
    const txHash = await walletClient.writeContract(request);
    console.log("Approve tx hash:", txHash);
}

async function transfer() {
    if (!window.ethereum) return;
    walletClient = createWalletClient({ transport: custom(window.ethereum) });
    const [account] = await walletClient.requestAddresses();

    publicClient = createPublicClient({ transport: custom(window.ethereum) });
    const recipient = recipientInput.value;
    const amount = transferAmountInput.value;
    const { request } = await publicClient.simulateContract({
        address: tokenContractAddress,
        abi: tokenABI,
        functionName: "transfer",
        args: [recipient, parseEther(amount)],
        account,
        chain: ethereumSepolia,
    });
    const txHash = await walletClient.writeContract(request);
    console.log("Transfer tx hash:", txHash);
}

async function transferFrom() {
    if (!window.ethereum) return;
    walletClient = createWalletClient({ transport: custom(window.ethereum) });
    const [account] = await walletClient.requestAddresses();

    publicClient = createPublicClient({ transport: custom(window.ethereum) });
    const from = fromAddressInput.value;
    const to = transferToAddressInput.value;
    const value = valueAmountInput.value;
    const { request } = await publicClient.simulateContract({
        address: tokenContractAddress,
        abi: tokenABI,
        functionName: "transferFrom",
        args: [from, to, parseEther(value)],
        account,
        chain: ethereumSepolia,
    });
    const txHash = await walletClient.writeContract(request);
    console.log("TransferFrom tx hash:", txHash);
}

async function allowance() {
    if (!window.ethereum) return;
    publicClient = createPublicClient({ transport: custom(window.ethereum) });
    const owner = ownerAddressInput.value;
    const spender = spenderAddressInput.value;
    const result = await publicClient.readContract({
        address: tokenContractAddress,
        abi: tokenABI,
        functionName: "allowance",
        args: [owner, spender],
        chain: ethereumSepolia,
    });
    alert(`Allowance: ${formatEther(result)} tokens`);
}

if (connectButton) connectButton.onclick = connect;
if (fundButton) fundButton.onclick = fund;
if (balanceButton) balanceButton.onclick = getBalance;
if (withdrawButton) withdrawButton.onclick = withdraw;

if (claimButton) claimButton.onclick = claim

if (approveButton) approveButton.onclick = approve;
if (transferButton) transferButton.onclick = transfer;
if (transferButton) transferFromButton.onclick = transferFrom;
if (allowanceButton) allowanceButton.onclick = allowance;
  
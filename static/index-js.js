// index-js.js

import {
    createWalletClient,
    custom,
    createPublicClient,
    parseEther,
    formatEther
} from "https://esm.sh/viem";
import { contractAddress, abi } from "./constants-js.js";

// manually define zkSync Sepolia
const zksyncSepolia = {
    id: 300,
    name: "zkSync Sepolia Testnet",
    network: "sepolia",
    rpcUrls: {
        default: {
            http: ["https://sepolia.era.zksync.dev"]
        }
    },
    nativeCurrency: {
        name: "Ether",
        symbol: "ETH",
        decimals: 18
    },
    blockExplorers: {
        default: {
            name: "zkSync Explorer",
            url: "https://sepolia.explorer.zksync.io"
        }
    }
};

const connectButton = document.getElementById("connectButton");
const fundButton = document.getElementById("fundButton");
const ethAmountInput = document.getElementById("ethAmount");
const balanceButton = document.getElementById("balanceButton");
const withdrawButton = document.getElementById("withdrawButton");

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
        address: contractAddress,
        abi,
        functionName: "fund",
        account,
        chain: zksyncSepolia,
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
        address: contractAddress,
        abi,
        functionName: "Withdraw", // must match exactly your ABI
        account,
        chain: zksyncSepolia,
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
        address: contractAddress,
        chain: zksyncSepolia
    });
    console.log("Contract balance:", formatEther(balance), "ETH");
}

connectButton.onclick = connect;
fundButton.onclick = fund;
balanceButton.onclick = getBalance;
withdrawButton.onclick = withdraw;
  
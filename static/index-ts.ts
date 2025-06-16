import {
    createWalletClient,
    createPublicClient,
    custom,
    parseEther,
    formatEther
} from "viem";
import "viem/window"
import type { WalletClient, PublicClient } from "viem";
import { contractAddress, abi } from "./constants-ts";

const connectButton = document.getElementById("connectButton") as HTMLButtonElement;
const fundButton = document.getElementById("fundButton") as HTMLButtonElement;
const ethAmountInput = document.getElementById("ethAmount") as HTMLInputElement;
const balanceButton = document.getElementById("balanceButton") as HTMLButtonElement;
const withdrawButton = document.getElementById("withdrawButton") as HTMLButtonElement;

let walletClient!: WalletClient;
let publicClient!: PublicClient;

/** Prompt MetaMask to connect */
async function connect(): Promise<void> {
    if (window.ethereum) {
        walletClient = createWalletClient({
            transport: custom(window.ethereum)
        });
        await walletClient.requestAddresses();
        connectButton.textContent = "Connected!";
    } else {
        connectButton.textContent = "Please install MetaMask!";
    }
}

/** Send ETH to the contract by calling its `fund` method */
async function fund(): Promise<void> {
    const ethAmount = ethAmountInput.value;
    console.log(`Funding with ${ethAmount} ETH...`);

    if (window.ethereum) {
        // (Re)initialize clients
        walletClient = createWalletClient({ transport: custom(window.ethereum) });
        publicClient = createPublicClient({ transport: custom(window.ethereum) });

        // Get connected account & chain ID
        const [connectedAccount] = await walletClient.requestAddresses();
        const chainId = await walletClient.getChainId();

        // Build the call data
        const { request } = await publicClient.simulateContract({
            address: contractAddress,
            abi,
            functionName: "fund",
            account: connectedAccount,
            chain: chainId,
            value: parseEther(ethAmount),
        });

        // Send transaction
        const txHash = await walletClient.writeContract(request);
        console.log("Funding tx hash:", txHash);
    } else {
        connectButton.textContent = "Please install MetaMask!";
    }
}

/** Call the contract's `withdraw` method */
async function withdraw(): Promise<void> {
    if (window.ethereum) {
        walletClient = createWalletClient({ transport: custom(window.ethereum) });
        publicClient = createPublicClient({ transport: custom(window.ethereum) });

        const [connectedAccount] = await walletClient.requestAddresses();
        const chainId = await walletClient.getChainId();

        const { request } = await publicClient.simulateContract({
            address: contractAddress,
            abi,
            functionName: "withdraw",
            account: connectedAccount,
            chain: chainId,
        });

        const txHash = await walletClient.writeContract(request);
        console.log("Withdrawal tx hash:", txHash);
    } else {
        connectButton.textContent = "Please install MetaMask!";
    }
}

/** Fetch and log the contract's ETH balance */
async function getBalance(): Promise<void> {
    if (window.ethereum) {
        publicClient = createPublicClient({ transport: custom(window.ethereum) });
        const balance = await publicClient.getBalance({ address: contractAddress });
        console.log("Contract balance:", formatEther(balance), "ETH");
    }
}

// Wire up UI events
connectButton.addEventListener("click", connect);
fundButton.addEventListener("click", fund);
balanceButton.addEventListener("click", getBalance);
withdrawButton.addEventListener("click", withdraw);
  
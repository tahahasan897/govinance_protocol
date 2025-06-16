import {createWalletClient, custom, createPublicClient, parseEther, formatEther} from "https://esm.sh/viem"
import {contractAddress, abi} from "constants-js.js"

const connectButton = document.getElementById("connectButton")
const fundButton = document.getElementById("fundButton")
const ethAmountInput = document.getElementById("ethAmount")
const balanceButton = document.getElementById("balanceButton")
const withdrawButton = document.getElementById("withdrawButton")

let walletClient
let publicClient

async function connect() {
    if (typeof window.ethereum !== "undefined") {

        walletClient = createWalletClient({
            transport: custom(window.ethereum)
        })
        await walletClient.requestAddresses()
        connectButton.innerHTML = "Connected!" 

    } else {
        connectButton.innerHTML = "Please install MetaMask!"
    }
}

async function fund() {
    const ethAmount = ethAmountInput.value
    console.log(`Funding with ${ethAmount}...`)

    if (typeof window.ethereum !== "undefined") {

        walletClient = createWalletClient({
            transport: custom(window.ethereum)
        })
        const [connectedAccount] = await walletClient.requestAddresses()

        publicClient = createPublicClient({
            transcport: custom(window.ethereum)
        })
        const { request } = await publicClient.simulateContract({
            address: contractAddress,
            abi: abi,
            functionName: "fund", 
            account: connectedAccount,
            chain:,
            value: parseEther(ethAmount),
        })
       
        const hash = await walletClient.writeContract(request)
        console.log(hash)

    } else {
        connectButton.innerHTML = "Please install MetaMask!"
    }
}

async function withdraw() {
    if (typeof window.ethereum !== "undefined") {
        walletClient = createWalletClient({
            transport: custom(window.ethereum),
        })
        const [connectedAccount] = await walletClient.requestAddresses()
        const currentChain = await getCurrentChain(walletClient)

        publicClient = createPublicClient({
            transport: custom(window.ethereum),
        })
        const { request } = await publicClient.simulateContract({
            address: contractAddress,
            abi: abi,
            functionName: "withdraw",
            account: connectedAccount,
            chain: ,
        })

        const hash = await walletClient.writeContract(request)
        console.log("Withdrawal transaction hash:", hash)
    } else {
        connectButton.innerHTML = "Please install MetaMask!"
    }
}

async function getBalance() {
    if (typeof window.ethereum !== "undefined") {

        publicClient = createPublicClient({
            transport: custom(window.ethereum)
        })
        const balance = await publicClient.getBalance({
            address: contractAddress
        })
        console.log(formatEther(balance))
    }
}

connectButton.onclick = connect 
fundButton.onclick = fund
balanceButton.onclick = getBalance
withdrawButton.onclick = withdraw
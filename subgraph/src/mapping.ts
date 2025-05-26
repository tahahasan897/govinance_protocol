// subgraph/src/mapping.ts

import { Transfer } from "../generated/Transcript/Transcript"
import { DailyVolume } from "../generated/schema"
import { BigInt } from "@graphprotocol/graph-ts"

export function handleTransfer(event: Transfer): void {
    let dayID = (event.block.timestamp.toI32() / 86400).toString()
    let daily = DailyVolume.load(dayID)
    if (!daily) {
        daily = new DailyVolume(dayID)
        daily.volume = BigInt.fromI32(0)
        daily.holderCount = 0
    }

    // Add the amount transferred
    daily.volume = daily.volume.plus(event.params.value)

    // (Optionally update holderCount here)

    daily.save()
}

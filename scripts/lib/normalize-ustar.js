import { readFileSync, writeFileSync } from "node:fs";

const TAR_BLOCK_SIZE = 512;
const TAR_SIZE_OFFSET = 124;
const TAR_SIZE_LENGTH = 12;
const TAR_CHECKSUM_OFFSET = 148;
const TAR_CHECKSUM_LENGTH = 8;
const TAR_TYPE_OFFSET = 156;
const TAR_MAGIC_OFFSET = 257;
const TAR_MAGIC_LENGTH = 6;
const TAR_DEVICE_OFFSET = 329;
const TAR_DEVICE_LENGTH = 16;

function isZeroBlock(buffer, offset) {
  for (let index = offset; index < offset + TAR_BLOCK_SIZE; index += 1) {
    if (buffer[index] !== 0) {
      return false;
    }
  }
  return true;
}

function parseOctal(buffer, offset, length, label) {
  const value = buffer
    .subarray(offset, offset + length)
    .toString("ascii")
    .replace(/\0.*$/, "")
    .trim();
  if (!/^[0-7]+$/.test(value)) {
    throw new Error(`invalid ustar ${label}: ${JSON.stringify(value)}`);
  }
  const parsed = Number.parseInt(value, 8);
  if (!Number.isSafeInteger(parsed)) {
    throw new Error(`ustar ${label} exceeds the safe integer range`);
  }
  return parsed;
}

function writeChecksum(buffer, offset) {
  buffer.fill(
    0x20,
    offset + TAR_CHECKSUM_OFFSET,
    offset + TAR_CHECKSUM_OFFSET + TAR_CHECKSUM_LENGTH,
  );
  let checksum = 0;
  for (let index = offset; index < offset + TAR_BLOCK_SIZE; index += 1) {
    checksum += buffer[index];
  }
  const octal = checksum.toString(8).padStart(6, "0");
  if (octal.length !== 6) {
    throw new Error("ustar header checksum exceeds the six-digit field");
  }
  buffer.write(octal, offset + TAR_CHECKSUM_OFFSET, 6, "ascii");
  buffer[offset + TAR_CHECKSUM_OFFSET + 6] = 0;
  buffer[offset + TAR_CHECKSUM_OFFSET + 7] = 0x20;
}

export function normalizeUstarBuffer(input) {
  if (!Buffer.isBuffer(input) || input.length % TAR_BLOCK_SIZE !== 0) {
    throw new Error("ustar archive must be a whole number of 512-byte blocks");
  }
  const archive = Buffer.from(input);
  let offset = 0;
  let foundEnd = false;
  while (offset + TAR_BLOCK_SIZE <= archive.length) {
    if (isZeroBlock(archive, offset)) {
      foundEnd = true;
      break;
    }
    const magic = archive
      .subarray(offset + TAR_MAGIC_OFFSET, offset + TAR_MAGIC_OFFSET + TAR_MAGIC_LENGTH)
      .toString("ascii");
    if (!magic.startsWith("ustar")) {
      throw new Error(`archive block ${offset / TAR_BLOCK_SIZE} is not ustar`);
    }
    const type = archive[offset + TAR_TYPE_OFFSET];
    if (type === "3".charCodeAt(0) || type === "4".charCodeAt(0)) {
      throw new Error("Device Kit archives cannot contain device nodes");
    }
    const size = parseOctal(
      archive,
      offset + TAR_SIZE_OFFSET,
      TAR_SIZE_LENGTH,
      "size",
    );

    // GNU tar versions disagree on whether unused device fields contain NULs
    // or octal zeroes. Canonical NUL fields make the archive cross-version
    // reproducible; the header checksum must then be recalculated.
    archive.fill(
      0,
      offset + TAR_DEVICE_OFFSET,
      offset + TAR_DEVICE_OFFSET + TAR_DEVICE_LENGTH,
    );
    writeChecksum(archive, offset);

    const dataBlocks = Math.ceil(size / TAR_BLOCK_SIZE);
    offset += TAR_BLOCK_SIZE + dataBlocks * TAR_BLOCK_SIZE;
  }
  if (!foundEnd) {
    throw new Error("ustar archive is missing its end marker");
  }
  return archive;
}

export function normalizeUstarArchive(path) {
  writeFileSync(path, normalizeUstarBuffer(readFileSync(path)));
}

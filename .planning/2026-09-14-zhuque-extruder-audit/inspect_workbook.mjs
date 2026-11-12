import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = process.argv[2];
if (!inputPath) throw new Error("xlsx path required");

const blob = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(blob);

const overview = await workbook.inspect({
  kind: "workbook,sheet,table,drawing,thread,definedName",
  include: "id,name,address,range,type,visibility,formula,text",
  maxChars: 20000,
  tableMaxRows: 12,
  tableMaxCols: 12,
  tableMaxCellChars: 120,
});
console.log("===OVERVIEW===");
console.log(overview.ndjson);

const matches = await workbook.inspect({
  kind: "match",
  searchTerm: "热端|喷嘴|挤出机|送料|喉管|加热棒|热敏|风扇|E3D|V6|BMG|泰坦|陶瓷|加热块|散热器|PT100|NTC|温度",
  options: { useRegex: true, maxResults: 300 },
  maxChars: 30000,
  summary: "朱雀热端与挤出系统相关条目",
});
console.log("===MATCHES===");
console.log(matches.ndjson);

for (const sheet of workbook.worksheets.items) {
  const used = sheet.getUsedRange();
  if (!used) continue;
  const values = used.values;
  const formulas = used.formulas;
  console.log(`===SHEET:${sheet.name}:${used.address}===`);
  console.log(JSON.stringify({ values, formulas }));
}

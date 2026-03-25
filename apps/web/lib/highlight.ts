import hljs from "highlight.js/lib/core";
import bash from "highlight.js/lib/languages/bash";
import javascript from "highlight.js/lib/languages/javascript";
import json from "highlight.js/lib/languages/json";
import markdown from "highlight.js/lib/languages/markdown";
import python from "highlight.js/lib/languages/python";
import sql from "highlight.js/lib/languages/sql";
import typescript from "highlight.js/lib/languages/typescript";
import xml from "highlight.js/lib/languages/xml";
import yaml from "highlight.js/lib/languages/yaml";

const registerLanguage = (name: string, language: Parameters<typeof hljs.registerLanguage>[1]) => {
  if (!hljs.getLanguage(name)) {
    hljs.registerLanguage(name, language);
  }
};

registerLanguage("ts", typescript);
registerLanguage("tsx", typescript);
registerLanguage("typescript", typescript);
registerLanguage("js", javascript);
registerLanguage("jsx", javascript);
registerLanguage("javascript", javascript);
registerLanguage("json", json);
registerLanguage("bash", bash);
registerLanguage("sh", bash);
registerLanguage("shell", bash);
registerLanguage("python", python);
registerLanguage("py", python);
registerLanguage("yaml", yaml);
registerLanguage("yml", yaml);
registerLanguage("sql", sql);
registerLanguage("md", markdown);
registerLanguage("markdown", markdown);
registerLanguage("html", xml);
registerLanguage("xml", xml);

export { hljs };

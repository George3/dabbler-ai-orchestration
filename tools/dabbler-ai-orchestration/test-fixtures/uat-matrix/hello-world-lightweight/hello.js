#!/usr/bin/env node
// Hello-world CLI. Set 001 greets; set 004 is mid-flight adding the
// farewell line below.
const name = process.argv[2] || "world";
console.log(`Hello, ${name}!`);

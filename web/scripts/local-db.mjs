import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import {resolve} from 'node:path';
export function database(filename=':memory:') {
  const sqlite=new DatabaseSync(filename);
  sqlite.exec('PRAGMA foreign_keys=ON');
  sqlite.exec('CREATE TABLE IF NOT EXISTS local_migrations(name TEXT PRIMARY KEY)');
  for(const name of readdirSync(resolve('drizzle')).filter(n=>n.endsWith('.sql')).sort()) {
    if(!sqlite.prepare('SELECT name FROM local_migrations WHERE name=?').get(name)) {
      sqlite.exec(readFileSync(resolve('drizzle',name),'utf8'));
      sqlite.prepare('INSERT INTO local_migrations(name) VALUES (?)').run(name);
    }
  }
  function prepare(sql) {
    let params=[];
    return {bind(...values){params=values;return this},async first(){return sqlite.prepare(sql).get(...params)||null},
      async all(){return {results:sqlite.prepare(sql).all(...params)}},async run(){const result=sqlite.prepare(sql).run(...params);return {meta:{changes:Number(result.changes)}}}};
  }
  return {prepare,sqlite,async batch(statements){sqlite.exec('BEGIN');try{const results=[];for(const statement of statements)results.push(await statement.run());sqlite.exec('COMMIT');return results}catch(error){sqlite.exec('ROLLBACK');throw error}}};
}

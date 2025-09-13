/**
 * Code Documentation System
 * 
 * Extracts, stores, and manages code documentation including functions, classes,
 * imports, and dependencies. Provides rich code analysis and documentation tracking.
 */

import { 
  CodeReference, 
  ProgrammingLanguage, 
  ICodeDocumentation,
  FunctionDocumentation,
  ClassDocumentation,
  ParameterDocumentation,
  ImportReference,
  DependencyReference
} from './rich-memory-types';

export class CodeDocumentation implements ICodeDocumentation {
  private codeReferences: Map<string, CodeReference> = new Map();
  private codeByFile: Map<string, string> = new Map(); // fileId -> codeId
  private functionsByLanguage: Map<ProgrammingLanguage, Set<string>> = new Map();
  private classesByLanguage: Map<ProgrammingLanguage, Set<string>> = new Map();

  constructor() {
    const languages: ProgrammingLanguage[] = ['python', 'javascript', 'typescript', 'java', 'cpp', 'go', 'rust', 'other'];
    languages.forEach(lang => {
      this.functionsByLanguage.set(lang, new Set());
      this.classesByLanguage.set(lang, new Set());
    });
  }

  addCode(code: CodeReference): void {
    this.codeReferences.set(code.codeId, code);
    this.codeByFile.set(code.fileId, code.codeId);
    
    // Update language indexes
    if (!this.functionsByLanguage.has(code.language)) {
      this.functionsByLanguage.set(code.language, new Set());
    }
    if (!this.classesByLanguage.has(code.language)) {
      this.classesByLanguage.set(code.language, new Set());
    }
    
    // Add functions to language index
    code.functions.forEach(func => {
      this.functionsByLanguage.get(code.language)!.add(func.name);
    });
    
    // Add classes to language index
    code.classes.forEach(cls => {
      this.classesByLanguage.get(code.language)!.add(cls.name);
    });
  }

  getCode(codeId: string): CodeReference | undefined {
    return this.codeReferences.get(codeId);
  }

  getCodeByFile(fileId: string): CodeReference | undefined {
    const codeId = this.codeByFile.get(fileId);
    return codeId ? this.codeReferences.get(codeId) : undefined;
  }

  getFunctionsByLanguage(language: ProgrammingLanguage): FunctionDocumentation[] {
    const functionNames = this.functionsByLanguage.get(language) || new Set();
    const functions: FunctionDocumentation[] = [];
    
    this.codeReferences.forEach(code => {
      if (code.language === language) {
        code.functions.forEach(func => {
          if (functionNames.has(func.name)) {
            functions.push(func);
          }
        });
      }
    });
    
    return functions;
  }

  getClassesByLanguage(language: ProgrammingLanguage): ClassDocumentation[] {
    const classNames = this.classesByLanguage.get(language) || new Set();
    const classes: ClassDocumentation[] = [];
    
    this.codeReferences.forEach(code => {
      if (code.language === language) {
        code.classes.forEach(cls => {
          if (classNames.has(cls.name)) {
            classes.push(cls);
          }
        });
      }
    });
    
    return classes;
  }

  updateCode(codeId: string, updates: Partial<CodeReference>): void {
    const existing = this.codeReferences.get(codeId);
    if (!existing) return;

    const updated: CodeReference = { ...existing, ...updates };
    this.codeReferences.set(codeId, updated);
  }

  removeCode(codeId: string): void {
    const code = this.codeReferences.get(codeId);
    if (!code) return;

    // Remove from file mapping
    this.codeByFile.delete(code.fileId);
    
    // Remove from language indexes
    code.functions.forEach(func => {
      const funcSet = this.functionsByLanguage.get(code.language);
      if (funcSet) funcSet.delete(func.name);
    });
    
    code.classes.forEach(cls => {
      const classSet = this.classesByLanguage.get(code.language);
      if (classSet) classSet.delete(cls.name);
    });
    
    this.codeReferences.delete(codeId);
  }

  getAllCode(): CodeReference[] {
    return Array.from(this.codeReferences.values());
  }

  // Code analysis and extraction methods
  analyzeCode(fileId: string, content: string, language: ProgrammingLanguage): CodeReference {
    const codeId = this.generateCodeId();
    
    const codeRef: CodeReference = {
      codeId,
      fileId,
      language,
      functions: this.extractFunctions(content, language),
      classes: this.extractClasses(content, language),
      imports: this.extractImports(content, language),
      dependencies: this.extractDependencies(content, language),
      documentation: this.extractCodeDocumentation(content),
      complexity: this.calculateCodeComplexity(content, language)
    };

    this.addCode(codeRef);
    return codeRef;
  }

  private extractFunctions(content: string, language: ProgrammingLanguage): FunctionDocumentation[] {
    const functions: FunctionDocumentation[] = [];
    
    switch (language) {
      case 'python':
        functions.push(...this.extractPythonFunctions(content));
        break;
      case 'javascript':
      case 'typescript':
        functions.push(...this.extractJavaScriptFunctions(content));
        break;
      case 'java':
        functions.push(...this.extractJavaFunctions(content));
        break;
    }
    
    return functions;
  }

  private extractPythonFunctions(content: string): FunctionDocumentation[] {
    const functions: FunctionDocumentation[] = [];
    const lines = content.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line) continue;
      
      const funcMatch = line.match(/def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)/);
      
      if (funcMatch && funcMatch[1] && funcMatch[2]) {
        const name = funcMatch[1];
        const paramsStr = funcMatch[2];
        const parameters = this.parsePythonParameters(paramsStr);
        
        // Find function end
        let endLine = i;
        const indentMatch = line.match(/^(\s*)/);
        let indentLevel = indentMatch?.[1]?.length || 0;
        
        for (let j = i + 1; j < lines.length; j++) {
          const currentLine = lines[j];
          if (!currentLine || currentLine.trim() === '') continue;
          
          const currentIndentMatch = currentLine.match(/^(\s*)/);
          const currentIndent = currentIndentMatch?.[1]?.length || 0;
          if (currentIndent <= indentLevel && currentLine.trim() !== '') {
            endLine = j - 1;
            break;
          }
          endLine = j;
        }
        
        // Extract documentation
        const docLines = [];
        for (let k = i + 1; k <= endLine; k++) {
          const docLine = lines[k];
          if (!docLine) continue;
          
          if (docLine.trim().startsWith('"""') || docLine.trim().startsWith("'''")) {
            // Found docstring start
            for (let l = k + 1; l <= endLine; l++) {
              const docContent = lines[l];
              if (!docContent) continue;
              
              if (docContent.trim().endsWith('"""') || docContent.trim().endsWith("'''")) {
                break;
              }
              docLines.push(docContent.trim());
            }
            break;
          }
        }
        
        functions.push({
          name,
          parameters,
          returnType: this.inferPythonReturnType(content, name),
          description: docLines.join(' '),
          examples: this.extractPythonExamples(content, name),
          complexity: this.calculateFunctionComplexity(content, i, endLine),
          lineStart: i + 1,
          lineEnd: endLine + 1
        });
      }
    }
    
    return functions;
  }

  private extractJavaScriptFunctions(content: string): FunctionDocumentation[] {
    const functions: FunctionDocumentation[] = [];
    
    // Function declarations
    const funcRegex = /function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)/g;
    let match;
    while ((match = funcRegex.exec(content)) !== null) {
      if (!match[1] || !match[2]) continue;
      
      const name = match[1];
      const paramsStr = match[2];
      const parameters = this.parseJavaScriptParameters(paramsStr);
      
      functions.push({
        name,
        parameters,
        returnType: 'any', // TypeScript would have better type inference
        description: this.extractJSDoc(content, match.index),
        examples: [],
        complexity: 1,
        lineStart: content.substring(0, match.index).split('\n').length,
        lineEnd: content.substring(0, match.index).split('\n').length + 1
      });
    }
    
    // Arrow functions and const functions
    const arrowFuncRegex = /(?:const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>/g;
    while ((match = arrowFuncRegex.exec(content)) !== null) {
      if (!match[1] || !match[2]) continue;
      
      const name = match[1];
      const paramsStr = match[2];
      const parameters = this.parseJavaScriptParameters(paramsStr);
      
      functions.push({
        name,
        parameters,
        returnType: 'any',
        description: '',
        examples: [],
        complexity: 1,
        lineStart: content.substring(0, match.index).split('\n').length,
        lineEnd: content.substring(0, match.index).split('\n').length + 1
      });
    }
    
    return functions;
  }

  private extractJavaFunctions(content: string): FunctionDocumentation[] {
    const functions: FunctionDocumentation[] = [];
    const lines = content.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line) continue;
      
      const methodMatch = line.match(/(?:public|private|protected)?\s*(?:static)?\s*(\w+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)/);
      
      if (methodMatch && methodMatch[1] && methodMatch[2] && methodMatch[3]) {
        const returnType = methodMatch[1];
        const name = methodMatch[2];
        const paramsStr = methodMatch[3];
        const parameters = this.parseJavaParameters(paramsStr);
        
        functions.push({
          name,
          parameters,
          returnType,
          description: this.extractJavaDoc(content, i),
          examples: [],
          complexity: 1,
          lineStart: i + 1,
          lineEnd: i + 1
        });
      }
    }
    
    return functions;
  }

  private extractClasses(content: string, language: ProgrammingLanguage): ClassDocumentation[] {
    const classes: ClassDocumentation[] = [];
    
    switch (language) {
      case 'python':
        classes.push(...this.extractPythonClasses(content));
        break;
      case 'javascript':
      case 'typescript':
        classes.push(...this.extractJavaScriptClasses(content));
        break;
      case 'java':
        classes.push(...this.extractJavaClasses(content));
        break;
    }
    
    return classes;
  }

  private extractPythonClasses(content: string): ClassDocumentation[] {
    const classes: ClassDocumentation[] = [];
    const lines = content.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line) continue;
      
      const classMatch = line.match(/class\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s*\([^)]*\))?/);
      
      if (classMatch && classMatch[1]) {
        const name = classMatch[1];
        const inheritanceMatch = line.match(/\(([^)]+)\)/);
        const inheritance = inheritanceMatch?.[1]?.split(',').map(s => s.trim()) || [];
        
        classes.push({
          name,
          methods: [], // Would need more complex parsing
          properties: [],
          description: '',
          inheritance,
          lineStart: i + 1,
          lineEnd: i + 1
        });
      }
    }
    
    return classes;
  }

  private extractJavaScriptClasses(content: string): ClassDocumentation[] {
    const classes: ClassDocumentation[] = [];
    const classRegex = /class\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+extends\s+([a-zA-Z_][a-zA-Z0-9_]*))?/g;
    let match;
    
    while ((match = classRegex.exec(content)) !== null) {
      if (!match[1]) continue;
      
      const name = match[1];
      const inheritance = match[2] ? [match[2]] : [];
      
      classes.push({
        name,
        methods: [],
        properties: [],
        description: '',
        inheritance,
        lineStart: content.substring(0, match.index).split('\n').length,
        lineEnd: content.substring(0, match.index).split('\n').length + 1
      });
    }
    
    return classes;
  }

  private extractJavaClasses(content: string): ClassDocumentation[] {
    const classes: ClassDocumentation[] = [];
    const classRegex = /(?:public|private|protected)?\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+extends\s+([a-zA-Z_][a-zA-Z0-9_]*))?(?:\s+implements\s+([^{]+))?/g;
    let match;
    
    while ((match = classRegex.exec(content)) !== null) {
      if (!match[1]) continue;
      
      const name = match[1];
      const inheritance = [];
      if (match[2]) inheritance.push(match[2]);
      if (match[3]) inheritance.push(...match[3].split(',').map(s => s.trim()));
      
      classes.push({
        name,
        methods: [],
        properties: [],
        description: '',
        inheritance,
        lineStart: content.substring(0, match.index).split('\n').length,
        lineEnd: content.substring(0, match.index).split('\n').length + 1
      });
    }
    
    return classes;
  }

  private extractImports(content: string, language: ProgrammingLanguage): ImportReference[] {
    const imports: ImportReference[] = [];
    const lines = content.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line) continue;
      
      const trimmedLine = line.trim();
      
      switch (language) {
        case 'python':
          const pythonImport = trimmedLine.match(/^(?:from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import\s+([^#]+)|import\s+([a-zA-Z_][a-zA-Z0-9_.]*))/);
          if (pythonImport) {
            if (pythonImport[1] && pythonImport[2]) {
              imports.push({
                module: pythonImport[1],
                imports: pythonImport[2].split(',').map(s => s.trim()),
                lineNumber: i + 1,
                type: 'from'
              });
            } else if (pythonImport[3]) {
              imports.push({
                module: pythonImport[3],
                imports: [],
                lineNumber: i + 1,
                type: 'import'
              });
            }
          }
          break;
          
        case 'javascript':
        case 'typescript':
          const jsImport = trimmedLine.match(/^import\s+(?:.*\s+from\s+)?['"]([^'"]+)['"]/);
          if (jsImport && jsImport[1]) {
            imports.push({
              module: jsImport[1],
              imports: [],
              lineNumber: i + 1,
              type: 'import'
            });
          }
          break;
          
        case 'java':
          const javaImport = trimmedLine.match(/^import\s+([a-zA-Z_][a-zA-Z0-9_.]*);/);
          if (javaImport && javaImport[1]) {
            imports.push({
              module: javaImport[1],
              imports: [],
              lineNumber: i + 1,
              type: 'import'
            });
          }
          break;
      }
    }
    
    return imports;
  }

  private extractDependencies(content: string, language: ProgrammingLanguage): DependencyReference[] {
    const dependencies: DependencyReference[] = [];
    
    // Extract from imports
    const imports = this.extractImports(content, language);
    imports.forEach(imp => {
      dependencies.push({
        name: imp.module,
        type: 'module',
        source: 'import'
      });
    });
    
    // Extract from package files
    if (language === 'javascript' || language === 'typescript') {
      const packageJsonMatch = content.match(/"([^"]+)":\s*"[^"]*"/g);
      if (packageJsonMatch) {
        packageJsonMatch.forEach(match => {
        const depMatch = match.match(/"([^"]+)":\s*"([^"]*)"/);
        if (depMatch && depMatch[1] && depMatch[2]) {
          dependencies.push({
            name: depMatch[1],
            version: depMatch[2],
            type: 'package',
            source: 'package.json'
          });
        }
        });
      }
    }
    
    return dependencies;
  }

  private extractCodeDocumentation(content: string): string {
    // Extract overall code documentation (comments, docstrings, etc.)
    const lines = content.split('\n');
    const docLines: string[] = [];
    
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('#') || trimmed.startsWith('//') || trimmed.startsWith('/*')) {
        docLines.push(trimmed);
      }
    }
    
    return docLines.join('\n').substring(0, 500); // Limit to 500 chars
  }

  private calculateCodeComplexity(content: string, _language: ProgrammingLanguage): number {
    let complexity = 1;
    
    const controlStructures = [
      'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'catch',
      'switch', 'case', 'break', 'continue', 'return', 'throw'
    ];
    
    controlStructures.forEach(structure => {
      const regex = new RegExp(`\\b${structure}\\b`, 'g');
      const matches = content.match(regex);
      if (matches) {
        complexity += matches.length;
      }
    });
    
    return complexity;
  }

  // Parameter parsing methods
  private parsePythonParameters(paramsStr: string): ParameterDocumentation[] {
    if (!paramsStr.trim()) return [];
    
    return paramsStr.split(',').map(param => {
      const trimmed = param.trim();
      const parts = trimmed.split('=');
      const name = parts[0]?.trim() || 'param';
      const defaultValue = parts[1]?.trim();
      
      return {
        name,
        type: 'any', // Python is dynamically typed
        description: '',
        required: !defaultValue,
        ...(defaultValue && { defaultValue })
      };
    });
  }

  private parseJavaScriptParameters(paramsStr: string): ParameterDocumentation[] {
    if (!paramsStr.trim()) return [];
    
    return paramsStr.split(',').map(param => {
      const trimmed = param.trim();
      const parts = trimmed.split('=');
      const name = parts[0]?.trim() || 'param';
      const defaultValue = parts[1]?.trim();
      
      return {
        name,
        type: 'any',
        description: '',
        required: !defaultValue,
        ...(defaultValue && { defaultValue })
      };
    });
  }

  private parseJavaParameters(paramsStr: string): ParameterDocumentation[] {
    if (!paramsStr.trim()) return [];
    
    return paramsStr.split(',').map(param => {
      const trimmed = param.trim();
      const parts = trimmed.split(' ');
      const type = parts[0] || 'void';
      const name = parts[1] || 'param';
      
      return {
        name,
        type,
        description: '',
        required: true
      };
    });
  }

  // Helper methods
  private inferPythonReturnType(content: string, functionName: string): string {
    // Simple return type inference
    const returnRegex = new RegExp(`def\\s+${functionName}[\\s\\S]*?return\\s+([^\\n]+)`, 'g');
    const match = returnRegex.exec(content);
    return match ? 'any' : 'None';
  }

  private extractPythonExamples(_content: string, _functionName: string): string[] {
    // Extract examples from docstrings or comments
    return [];
  }

  private extractJSDoc(_content: string, _index: number): string {
    // Extract JSDoc comments
    return '';
  }

  private extractJavaDoc(_content: string, _lineIndex: number): string {
    // Extract JavaDoc comments
    return '';
  }

  private calculateFunctionComplexity(_content: string, _startLine: number, _endLine: number): number {
    // Calculate cyclomatic complexity for a function
    return 1;
  }

  private generateCodeId(): string {
    return `code_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Query methods
  getFunctionsByName(name: string): FunctionDocumentation[] {
    const functions: FunctionDocumentation[] = [];
    this.codeReferences.forEach(code => {
      code.functions.forEach(func => {
        if (func.name === name) {
          functions.push(func);
        }
      });
    });
    return functions;
  }

  getClassesByName(name: string): ClassDocumentation[] {
    const classes: ClassDocumentation[] = [];
    this.codeReferences.forEach(code => {
      code.classes.forEach(cls => {
        if (cls.name === name) {
          classes.push(cls);
        }
      });
    });
    return classes;
  }

  getStats(): {
    totalCode: number;
    totalFunctions: number;
    totalClasses: number;
    byLanguage: Record<ProgrammingLanguage, number>;
    averageComplexity: number;
  } {
    const allCode = this.getAllCode();
    const totalFunctions = allCode.reduce((sum, code) => sum + code.functions.length, 0);
    const totalClasses = allCode.reduce((sum, code) => sum + code.classes.length, 0);
    const totalComplexity = allCode.reduce((sum, code) => sum + code.complexity, 0);
    
    const byLanguage: Record<ProgrammingLanguage, number> = {} as any;
    allCode.forEach(code => {
      byLanguage[code.language] = (byLanguage[code.language] || 0) + 1;
    });
    
    return {
      totalCode: allCode.length,
      totalFunctions,
      totalClasses,
      byLanguage,
      averageComplexity: allCode.length > 0 ? totalComplexity / allCode.length : 0
    };
  }
}

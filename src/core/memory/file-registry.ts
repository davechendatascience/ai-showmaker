/**
 * File Registry System
 * 
 * Manages file references, metadata, and content tracking for the rich memory system.
 * Provides file operations tracking, content analysis, and metadata extraction.
 */

import { 
  FileReference, 
  FileType, 
  ProgrammingLanguage, 
  IFileRegistry,
  FileMetadata 
} from './rich-memory-types';
import * as crypto from 'crypto';

export class FileRegistry implements IFileRegistry {
  private files: Map<string, FileReference> = new Map();
  private filesByType: Map<FileType, Set<string>> = new Map();
  private filesByLanguage: Map<ProgrammingLanguage, Set<string>> = new Map();
  private filesByTask: Map<string, Set<string>> = new Map();

  constructor() {
    // Initialize type and language maps
    const fileTypes: FileType[] = ['code', 'documentation', 'data', 'config', 'output'];
    const languages: ProgrammingLanguage[] = ['python', 'javascript', 'typescript', 'java', 'cpp', 'go', 'rust', 'other'];
    
    fileTypes.forEach(type => this.filesByType.set(type, new Set()));
    languages.forEach(lang => this.filesByLanguage.set(lang, new Set()));
  }

  addFile(file: FileReference, taskId?: string): void {
    this.files.set(file.fileId, file);
    
    // Update type index
    if (!this.filesByType.has(file.fileType)) {
      this.filesByType.set(file.fileType, new Set());
    }
    this.filesByType.get(file.fileType)!.add(file.fileId);
    
    // Update language index
    if (file.metadata?.language) {
      if (!this.filesByLanguage.has(file.metadata.language)) {
        this.filesByLanguage.set(file.metadata.language, new Set());
      }
      this.filesByLanguage.get(file.metadata.language)!.add(file.fileId);
    }
    
    // Update task index
    if (taskId) {
      if (!this.filesByTask.has(taskId)) {
        this.filesByTask.set(taskId, new Set());
      }
      this.filesByTask.get(taskId)!.add(file.fileId);
    }
  }

  getFile(fileId: string): FileReference | undefined {
    return this.files.get(fileId);
  }

  getFilesByType(fileType: FileType): FileReference[] {
    const fileIds = this.filesByType.get(fileType) || new Set();
    return Array.from(fileIds).map(id => this.files.get(id)!).filter(Boolean);
  }

  getFilesByLanguage(language: ProgrammingLanguage): FileReference[] {
    const fileIds = this.filesByLanguage.get(language) || new Set();
    return Array.from(fileIds).map(id => this.files.get(id)!).filter(Boolean);
  }

  getFilesByTask(taskId: string): FileReference[] {
    const fileIds = this.filesByTask.get(taskId) || new Set();
    return Array.from(fileIds).map(id => this.files.get(id)!).filter(Boolean);
  }

  updateFile(fileId: string, updates: Partial<FileReference>): void {
    const existingFile = this.files.get(fileId);
    if (!existingFile) return;

    const updatedFile: FileReference = {
      ...existingFile,
      ...updates,
      modifiedAt: Date.now()
    };

    this.files.set(fileId, updatedFile);
  }

  removeFile(fileId: string): void {
    const file = this.files.get(fileId);
    if (!file) return;

    // Remove from type index
    const typeSet = this.filesByType.get(file.fileType);
    if (typeSet) {
      typeSet.delete(fileId);
    }

    // Remove from language index
    if (file.metadata?.language) {
      const langSet = this.filesByLanguage.get(file.metadata.language);
      if (langSet) {
        langSet.delete(fileId);
      }
    }

    this.files.delete(fileId);
  }

  getAllFiles(): FileReference[] {
    return Array.from(this.files.values());
  }

  // Utility methods for file analysis
  createFileReference(
    filePath: string, 
    content: string, 
    fileType: FileType, 
    createdBy: string,
    metadata?: Partial<FileMetadata>
  ): FileReference {
    const fileId = this.generateFileId();
    const checksum = this.calculateChecksum(content);
    
    // Analyze content for metadata
    const analyzedMetadata = this.analyzeFileContent(content, fileType, metadata);
    
    const fileRef: FileReference = {
      fileId,
      filePath,
      fileType,
      content,
      size: content.length,
      createdBy,
      createdAt: Date.now(),
      modifiedAt: Date.now(),
      metadata: analyzedMetadata,
      checksum
    };

    this.addFile(fileRef);
    return fileRef;
  }

  private analyzeFileContent(
    content: string, 
    fileType: FileType, 
    metadata?: Partial<FileMetadata>
  ): FileMetadata {
    const analyzed: FileMetadata = {
      lineCount: content.split('\n').length,
      ...metadata
    };

    if (fileType === 'code') {
      // Detect programming language
      analyzed.language = this.detectLanguage(content);
      
      if (analyzed.language) {
        // Extract code elements based on language
        analyzed.functions = this.extractFunctions(content, analyzed.language);
        analyzed.classes = this.extractClasses(content, analyzed.language);
        analyzed.imports = this.extractImports(content, analyzed.language);
        analyzed.dependencies = this.extractDependencies(content, analyzed.language);
        analyzed.complexity = this.calculateComplexity(content, analyzed.language);
      }
    } else if (fileType === 'documentation') {
      // Analyze documentation
      analyzed.documentation = this.extractDocumentationSummary(content);
      // analyzed.wordCount = this.countWords(content); // Not in FileMetadata interface
    }

    return analyzed;
  }

  private detectLanguage(content: string): ProgrammingLanguage {
    // Simple language detection based on file patterns
    if (content.includes('def ') && content.includes('import ')) return 'python';
    if (content.includes('function ') && content.includes('const ')) return 'javascript';
    if (content.includes('interface ') && content.includes('type ')) return 'typescript';
    if (content.includes('public class ') && content.includes('import ')) return 'java';
    if (content.includes('#include ') && content.includes('int main')) return 'cpp';
    if (content.includes('package ') && content.includes('func ')) return 'go';
    if (content.includes('fn ') && content.includes('use ')) return 'rust';
    
    return 'other';
  }

  private extractFunctions(content: string, language: ProgrammingLanguage): string[] {
    const functions: string[] = [];
    
    switch (language) {
      case 'python':
        const pythonFuncRegex = /def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/g;
        let match;
        while ((match = pythonFuncRegex.exec(content)) !== null) {
          if (match[1]) functions.push(match[1]);
        }
        break;
        
      case 'javascript':
      case 'typescript':
        const jsFuncRegex = /(?:function\s+([a-zA-Z_][a-zA-Z0-9_]*)|const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s+)?\(|([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*=>)/g;
        while ((match = jsFuncRegex.exec(content)) !== null) {
          const funcName = match[1] || match[2] || match[3];
          if (funcName) functions.push(funcName);
        }
        break;
        
      case 'java':
        const javaFuncRegex = /(?:public|private|protected)?\s*(?:static)?\s*\w+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/g;
        while ((match = javaFuncRegex.exec(content)) !== null) {
          if (match[1]) functions.push(match[1]);
        }
        break;
    }
    
    return functions;
  }

  private extractClasses(content: string, language: ProgrammingLanguage): string[] {
    const classes: string[] = [];
    
    switch (language) {
      case 'python':
        const pythonClassRegex = /class\s+([a-zA-Z_][a-zA-Z0-9_]*)/g;
        let match;
        while ((match = pythonClassRegex.exec(content)) !== null) {
          if (match[1]) classes.push(match[1]);
        }
        break;
        
      case 'javascript':
      case 'typescript':
        const jsClassRegex = /class\s+([a-zA-Z_][a-zA-Z0-9_]*)/g;
        while ((match = jsClassRegex.exec(content)) !== null) {
          if (match[1]) classes.push(match[1]);
        }
        break;
        
      case 'java':
        const javaClassRegex = /(?:public|private|protected)?\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)/g;
        while ((match = javaClassRegex.exec(content)) !== null) {
          if (match[1]) classes.push(match[1]);
        }
        break;
    }
    
    return classes;
  }

  private extractImports(content: string, language: ProgrammingLanguage): string[] {
    const imports: string[] = [];
    
    switch (language) {
      case 'python':
        const pythonImportRegex = /(?:from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import|import\s+([a-zA-Z_][a-zA-Z0-9_.]*))/g;
        let match;
        while ((match = pythonImportRegex.exec(content)) !== null) {
          const importName = match[1] || match[2];
          if (importName) imports.push(importName);
        }
        break;
        
      case 'javascript':
      case 'typescript':
        const jsImportRegex = /(?:import\s+.*\s+from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))/g;
        while ((match = jsImportRegex.exec(content)) !== null) {
          const importName = match[1] || match[2];
          if (importName) imports.push(importName);
        }
        break;
        
      case 'java':
        const javaImportRegex = /import\s+([a-zA-Z_][a-zA-Z0-9_.]*);/g;
        while ((match = javaImportRegex.exec(content)) !== null) {
          if (match[1]) imports.push(match[1]);
        }
        break;
    }
    
    return imports;
  }

  private extractDependencies(content: string, language: ProgrammingLanguage): string[] {
    const dependencies: string[] = [];
    
    // Extract from imports
    const imports = this.extractImports(content, language);
    dependencies.push(...imports);
    
    // Extract from package.json, requirements.txt, etc.
    if (language === 'javascript' || language === 'typescript') {
      const packageJsonRegex = /"([^"]+)":\s*"[^"]*"/g;
      let match;
      while ((match = packageJsonRegex.exec(content)) !== null) {
        if (match[1]) dependencies.push(match[1]);
      }
    } else if (language === 'python') {
      const requirementsRegex = /^([a-zA-Z0-9_-]+)/gm;
      let match;
      while ((match = requirementsRegex.exec(content)) !== null) {
        if (match[1]) dependencies.push(match[1]);
      }
    }
    
    return dependencies;
  }

  private calculateComplexity(content: string, _language: ProgrammingLanguage): number {
    // Simple complexity calculation based on control structures
    let complexity = 1; // Base complexity
    
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

  private extractDocumentationSummary(content: string): string {
    // Extract first paragraph or summary from documentation
    const lines = content.split('\n');
    const summaryLines: string[] = [];
    
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#') && !trimmed.startsWith('*')) {
        summaryLines.push(trimmed);
        if (summaryLines.length >= 3) break; // Take first 3 lines
      }
    }
    
    return summaryLines.join(' ').substring(0, 200); // Limit to 200 chars
  }


  private generateFileId(): string {
    return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private calculateChecksum(content: string): string {
    return crypto.createHash('md5').update(content).digest('hex');
  }

  // Query methods
  getFilesWithDocumentation(): FileReference[] {
    return this.getAllFiles().filter(file => 
      file.metadata?.documentation && file.metadata.documentation.length > 50
    );
  }

  getCodeFiles(): FileReference[] {
    return this.getFilesByType('code');
  }

  getDocumentationFiles(): FileReference[] {
    return this.getFilesByType('documentation');
  }

  getFilesByCreator(createdBy: string): FileReference[] {
    return this.getAllFiles().filter(file => file.createdBy === createdBy);
  }

  getRecentFiles(minutes: number = 60): FileReference[] {
    const cutoff = Date.now() - (minutes * 60 * 1000);
    return this.getAllFiles().filter(file => file.createdAt > cutoff);
  }

  // Statistics
  getStats(): {
    totalFiles: number;
    byType: Record<FileType, number>;
    byLanguage: Record<ProgrammingLanguage, number>;
    totalSize: number;
    averageSize: number;
  } {
    const files = this.getAllFiles();
    const byType: Record<FileType, number> = {} as any;
    const byLanguage: Record<ProgrammingLanguage, number> = {} as any;
    
    files.forEach(file => {
      byType[file.fileType] = (byType[file.fileType] || 0) + 1;
      if (file.metadata?.language) {
        byLanguage[file.metadata.language] = (byLanguage[file.metadata.language] || 0) + 1;
      }
    });
    
    const totalSize = files.reduce((sum, file) => sum + file.size, 0);
    
    return {
      totalFiles: files.length,
      byType,
      byLanguage,
      totalSize,
      averageSize: files.length > 0 ? totalSize / files.length : 0
    };
  }
}
